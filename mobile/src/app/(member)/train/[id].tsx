import { useRef, useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import * as Crypto from 'expo-crypto';
import { useLocalSearchParams } from 'expo-router';
import { Image, Text, View } from 'react-native';

import { Action, Busy, Card, Field, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { apiUrl, errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';
import { exerciseImage, type Exercise, type ExerciseHistoryPage, type WorkoutToday } from '@/lib/training';

export default function ExerciseDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { request, user } = useAuth();
  const queryClient = useQueryClient();
  const exercise = useQuery({ queryKey: ['training', 'exercise', user?.id, id], queryFn: ({ signal }) => request<Exercise>(`/training/exercises/${id}`, { signal }), enabled: !!id });
  const history = useQuery({ queryKey: ['training', 'exercise-history', user?.id, id], queryFn: ({ signal }) => request<ExerciseHistoryPage>(`/training/exercises/${id}/history?page_size=10`, { signal }), enabled: !!id });
  const today = useQuery({ queryKey: ['training', 'workout', 'today', user?.id], queryFn: ({ signal }) => request<WorkoutToday>('/training/workouts/today', { signal }) });
  const saved = (value: WorkoutToday) => { queryClient.setQueryData(['training', 'workout', 'today', user?.id], value); void Promise.all([queryClient.invalidateQueries({ queryKey: ['training', 'history', user?.id] }), queryClient.invalidateQueries({ queryKey: ['training', 'muscle-map', user?.id] }), queryClient.invalidateQueries({ queryKey: ['training', 'exercise-history', user?.id, id] })]); };
  return <Screen><PageTop title="Exercise guide" fallback="/(member)/(tabs)/train" />
    {exercise.isLoading ? <Busy label="Loading exercise" /> : null}
    {exercise.isError ? <Message title="Exercise unavailable" detail={errorMessage(exercise.error)} action="Retry" onAction={() => void exercise.refetch()} tone="error" /> : null}
    {exercise.data ? <><View style={{ height: 220, borderRadius: 18, backgroundColor: colors.primarySurface, alignItems: 'center', justifyContent: 'center', overflow: 'hidden', marginBottom: 16 }}>{exercise.data.has_image ? <Image source={{ uri: apiUrl(exerciseImage(exercise.data)) }} style={{ width: '100%', height: '100%' }} resizeMode="cover" accessibilityLabel={`${exercise.data.name} exercise guide image`} /> : <Ionicons name="barbell-outline" size={70} color={colors.primary} />}</View>
      <Text style={textStyles.accent}>{exercise.data.region.toUpperCase()} BODY · YPTRAIN</Text><Text style={[textStyles.subheading, { fontSize: 30, marginTop: 8 }]}>{exercise.data.name}</Text><Text style={[textStyles.muted, { marginVertical: 12 }]}>{exercise.data.description}</Text>
      {exercise.data.is_illustrative ? <Message title="Illustrative guide" detail="Confirm on-site equipment availability where applicable." /> : null}
      <Card><Text style={textStyles.subheading}>How to use</Text><Text style={textStyles.body}>{exercise.data.usage_steps}</Text></Card>
      <Card><Text style={textStyles.subheading}>Muscles</Text><Text style={textStyles.body}>Primary: {exercise.data.primary_muscles.join(', ')}</Text><Text style={textStyles.body}>Secondary: {exercise.data.secondary_muscles.join(', ') || 'None listed'}</Text></Card>
      <Card><Text style={textStyles.subheading}>Safety note</Text><Text style={textStyles.body}>{exercise.data.safety_note}</Text></Card>
      {today.isLoading ? <Busy label="Checking today's gym visit" /> : null}{today.isError ? <Message title="Workout unavailable" detail={errorMessage(today.error)} action="Retry" onAction={() => void today.refetch()} tone="error" /> : null}
      {today.data?.eligible ? <WorkoutForm exercise={exercise.data} request={request} onSaved={saved} /> : today.data ? <Message title="Check-in required" detail={today.data.reason ?? ''} action="Check again" onAction={() => void today.refetch()} /> : null}
      {today.data?.session ? <Card><Text style={textStyles.subheading}>{`Today's workout · ${today.data.gym_date}`}</Text>{today.data.session.exercises.map((item) => <View key={item.id}><Text style={textStyles.body}>{item.name}</Text><Text style={textStyles.muted}>{item.sets.map((set) => `${set.set_order}: ${set.reps} reps × ${set.weight} ${set.unit}`).join(' · ')}</Text></View>)}</Card> : null}
      <Card><Text style={textStyles.subheading}>Your prior sessions</Text><Text style={textStyles.muted}>Descriptive comparisons use your previous logged session. They are not a next-session target.</Text>{history.isLoading ? <Busy label="Loading prior sessions" /> : null}{history.isError ? <Message title="Prior sessions unavailable" detail={errorMessage(history.error)} action="Retry" onAction={() => void history.refetch()} tone="error" /> : null}{history.data?.items.length === 0 ? <Message title="No prior sessions" detail="Your logged sessions for this exercise will appear here." /> : null}{history.data?.items.map((item) => <View key={item.workout_exercise_id} style={{ borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 10, gap: 4 }}><Text style={textStyles.body}>{item.workout_date}</Text><Text style={textStyles.muted}>{item.comparison_to_previous ? `Sets ${item.comparison_to_previous.sets} · reps ${item.comparison_to_previous.reps} · load ${item.comparison_to_previous.external_load}` : 'First recorded baseline'}</Text><Text style={textStyles.body}>{item.set_count} sets · {item.total_reps} total reps · {item.max_external_load_kg} kg max external load</Text><Text style={textStyles.muted}>{item.sets.map((set) => `${set.set_order}: ${set.reps} reps × ${set.weight} ${set.unit}`).join(' · ')}</Text></View>)}</Card>
    </> : null}
  </Screen>;
}

type SetDraft = { reps: string; weight: string; unit: 'kg' | 'lb' };
const blankSet = (): SetDraft => ({ reps: '', weight: '0', unit: 'kg' });

function WorkoutForm({ exercise, request, onSaved }: { exercise: Exercise; request: <T>(path: string, options?: { method?: 'POST'; body?: unknown }) => Promise<T>; onSaved: (value: WorkoutToday) => void }) {
  const [count, setCount] = useState(1);
  const [rows, setRows] = useState<SetDraft[]>(() => Array.from({ length: 10 }, blankSet));
  const [key, setKey] = useState(() => Crypto.randomUUID());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const submitting = useRef(false);
  const change = (index: number, patch: Partial<SetDraft>) => { setRows((previous) => previous.map((row, i) => i === index ? { ...row, ...patch } : row)); setKey(Crypto.randomUUID()); setError(''); setSaved(false); };
  const changeCount = (next: number) => { setCount(next); setKey(Crypto.randomUUID()); setSaved(false); setError(''); };
  const submit = async () => {
    if (submitting.current) return;
    const sets = rows.slice(0, count);
    if (sets.some((row) => !Number.isInteger(Number(row.reps)) || Number(row.reps) < 1 || Number(row.reps) > 1000 || !/^\d+(\.\d{1,2})?$/.test(row.weight) || Number(row.weight) > 9999.99)) { setError('Enter 1–1000 whole reps and a non-negative weight up to 9999.99 for each set.'); return; }
    submitting.current = true; setBusy(true); setError('');
    try {
      const result = await request<WorkoutToday>('/training/workouts/today/exercises', { method: 'POST', body: { exercise_id: exercise.id, idempotency_key: key, sets: sets.map((row) => ({ reps: Number(row.reps), weight: row.weight, unit: row.unit })) } });
      onSaved(result); setSaved(true); setKey(Crypto.randomUUID()); setRows(Array.from({ length: 10 }, blankSet)); setCount(1);
    } catch (cause) { setError(errorMessage(cause)); }
    finally { submitting.current = false; setBusy(false); }
  };
  return <Card><Text style={textStyles.subheading}>Add Exercise</Text><Text style={textStyles.muted}>Record external load in kg or lb. Use 0 kg for bodyweight or no added load; it does not mean zero effort.</Text>
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}><View style={{ flex: 1 }}><Action label="− Remove set" outline disabled={busy || count <= 1} onPress={() => changeCount(count - 1)} /></View><Text accessibilityLabel={`${count} sets`} style={textStyles.body}>{count} {count === 1 ? 'set' : 'sets'}</Text><View style={{ flex: 1 }}><Action label="+ Add set" outline disabled={busy || count >= 10} onPress={() => changeCount(count + 1)} /></View></View>
    {rows.slice(0, count).map((row, index) => <View key={index} style={{ gap: 8, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 12 }}><Text style={textStyles.body}>Set {index + 1}</Text><Field label={`Set ${index + 1} reps`} value={row.reps} onChangeText={(value) => change(index, { reps: value })} keyboardType="number-pad" editable={!busy} /><Field label={`Set ${index + 1} external weight`} value={row.weight} onChangeText={(value) => change(index, { weight: value })} keyboardType="decimal-pad" editable={!busy} /><View style={{ flexDirection: 'row', gap: 8 }}><View style={{ flex: 1 }}><Action label={`kg${row.unit === 'kg' ? ' selected' : ''}`} outline={row.unit !== 'kg'} disabled={busy} onPress={() => change(index, { unit: 'kg' })} /></View><View style={{ flex: 1 }}><Action label={`lb${row.unit === 'lb' ? ' selected' : ''}`} outline={row.unit !== 'lb'} disabled={busy} onPress={() => change(index, { unit: 'lb' })} /></View></View></View>)}
    {error ? <Message title="Could not save exercise" detail={error} tone="error" /> : null}{saved ? <Message title="Exercise saved" detail="It now appears in today's workout." tone="success" /> : null}<Action label={busy ? 'Saving…' : 'Save exercise'} disabled={busy} onPress={() => void submit()} />
  </Card>;
}
