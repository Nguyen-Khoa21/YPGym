import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import { Action, Busy, Card, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { activeGyms } from '@/lib/gyms';
import {
  daysOptions, fromBoolean, goalOptions, toBoolean, windowOptions, yesNoOptions,
  type OnboardingState, type Option,
} from '@/lib/onboarding';
import { queryClient } from '@/lib/query';
import { colors } from '@/lib/theme';
import type { GymLocation } from '@/lib/types';

type Answers = Record<'new' | 'uncrowded' | 'gym' | 'goal' | 'window' | 'days' | 'classes' | 'pt', string>;
const empty: Answers = { new: '', uncrowded: '', gym: '', goal: '', window: '', days: '', classes: '', pt: '' };

function Group({ legend, options, value, onChange, optional = false, error }: { legend: string; options: Option[]; value: string; onChange: (value: string) => void; optional?: boolean; error?: string }) {
  return <View accessibilityRole="radiogroup" style={{ marginBottom: 6 }}>
    <Text style={[textStyles.subheading, { marginTop: 14, marginBottom: 8 }]}>{legend}{optional ? <Text style={textStyles.muted}>  Optional</Text> : null}</Text>
    {options.map((option) => <Pressable accessibilityRole="radio" accessibilityState={{ selected: value === option.value }} key={option.value} onPress={() => onChange(option.value)}>
      <Card accent={value === option.value}><Text style={textStyles.body}>{option.label}</Text></Card>
    </Pressable>)}
    {error ? <Text style={{ color: colors.danger }}>{error}</Text> : null}
  </View>;
}

export default function OnboardingScreen() {
  const { request, user } = useAuth();
  const [answers, setAnswers] = useState<Answers>(empty);
  const [loaded, setLoaded] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const state = useQuery({ queryKey: ['onboarding', user?.id], queryFn: ({ signal }) => request<OnboardingState>('/users/me/onboarding', { signal }) });
  const gyms = useQuery({ queryKey: ['gyms'], queryFn: ({ signal }) => request<GymLocation[]>('/gyms', { signal }) });

  useEffect(() => {
    if (!state.data || loaded) return;
    setLoaded(true);
    setAnswers({
      new: fromBoolean(state.data.is_new_to_gym), uncrowded: fromBoolean(state.data.prefers_uncrowded_hours),
      gym: state.data.closer_gym_id ?? '', goal: state.data.main_goal ?? '', window: state.data.training_window ?? '',
      days: state.data.days_per_week ?? '', classes: fromBoolean(state.data.interested_in_classes), pt: fromBoolean(state.data.interested_in_personal_trainer),
    });
  }, [state.data, loaded]);

  function done() {
    void queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    void queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    if (router.canGoBack()) router.back(); else router.replace('/(member)/(tabs)/dashboard');
  }
  const save = useMutation({
    mutationFn: () => request<OnboardingState>('/users/me/onboarding', { method: 'PUT', body: {
      is_new_to_gym: toBoolean(answers.new), prefers_uncrowded_hours: toBoolean(answers.uncrowded), closer_gym_id: answers.gym || null,
      main_goal: answers.goal || null, training_window: answers.window || null, days_per_week: answers.days || null,
      interested_in_classes: toBoolean(answers.classes), interested_in_personal_trainer: toBoolean(answers.pt),
    } }),
    onSuccess: done,
  });
  const skip = useMutation({ mutationFn: () => request<OnboardingState>('/users/me/onboarding/skip', { method: 'POST' }), onSuccess: done });
  const set = (key: keyof Answers) => (value: string) => setAnswers((current) => ({ ...current, [key]: value }));
  const gymOptions = activeGyms(gyms.data).map((gym) => ({ value: gym.id, label: gym.name }));
  const busy = save.isPending || skip.isPending;
  const failure = save.error ?? skip.error;

  function submit() {
    setShowErrors(true);
    if (!answers.new || !answers.uncrowded || !answers.gym) return;
    save.mutate();
  }

  return <Screen><PageTop title="Training preferences" fallback="/(member)/(tabs)/dashboard" />
    <Heading eyebrow="Welcome to YPGym" title="A few quick questions" detail="We use your answers to suggest quiet hours and your closest gym. They are private, you can change them later, and they never include health information." />
    {state.isLoading || gyms.isLoading ? <Busy label="Loading questions" /> : null}
    {state.isError ? <Message title="Questions unavailable" detail={errorMessage(state.error)} action="Retry" onAction={() => void state.refetch()} tone="error" /> : null}
    {state.data ? <>
      <Group legend="Are you new to the gym?" options={yesNoOptions} value={answers.new} onChange={set('new')} error={showErrors && !answers.new ? 'Choose Yes or No.' : undefined} />
      <Group legend="Would you like to work out in uncrowded hours?" options={yesNoOptions} value={answers.uncrowded} onChange={set('uncrowded')} error={showErrors && !answers.uncrowded ? 'Choose Yes or No.' : undefined} />
      <Group legend="Which location are you closer to?" options={gymOptions} value={answers.gym} onChange={set('gym')} error={showErrors && !answers.gym ? 'Choose the location closest to you.' : undefined} />
      <Group legend="What is your main goal?" options={goalOptions} value={answers.goal} onChange={set('goal')} optional />
      <Group legend="When can you usually train?" options={windowOptions} value={answers.window} onChange={set('window')} optional />
      <Group legend="How many days a week?" options={daysOptions} value={answers.days} onChange={set('days')} optional />
      <Group legend="Interested in group classes?" options={yesNoOptions} value={answers.classes} onChange={set('classes')} optional />
      <Group legend="Interested in a personal trainer?" options={yesNoOptions} value={answers.pt} onChange={set('pt')} optional />
      {failure ? <Message title="Could not save" detail={errorMessage(failure)} tone="error" /> : null}
      <Action label={save.isPending ? 'Saving…' : 'Save answers'} onPress={submit} disabled={busy} />
      <Action label="Skip for now" onPress={() => skip.mutate()} disabled={busy} outline />
    </> : null}
  </Screen>;
}
