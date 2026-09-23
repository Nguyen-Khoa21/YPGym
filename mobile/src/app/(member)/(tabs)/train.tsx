import { useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Image, Pressable, Text, View } from 'react-native';

import { Action, Brand, Busy, Card, Field, Heading, Message, Screen, textStyles } from '@/components/ui';
import { apiUrl, errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';
import { exerciseImage, muscles, type Exercise, type ExercisePage, type Muscle, type WorkoutToday } from '@/lib/training';

export default function TrainScreen() {
  const { request, user } = useAuth();
  const [region, setRegion] = useState<'all' | 'upper' | 'lower'>('all');
  const [search, setSearch] = useState('');
  const [muscle, setMuscle] = useState<Muscle | ''>('');
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page: String(page), page_size: '30' });
  if (region !== 'all') params.set('region', region);
  if (search.trim()) params.set('search', search.trim());
  if (muscle) params.set('muscle', muscle);
  const catalogue = useQuery({ queryKey: ['training', 'exercises', user?.id, params.toString()], queryFn: ({ signal }) => request<ExercisePage>(`/training/exercises?${params}`, { signal }) });
  const today = useQuery({ queryKey: ['training', 'workout', 'today', user?.id], queryFn: ({ signal }) => request<WorkoutToday>('/training/workouts/today', { signal }) });
  return <Screen refreshing={catalogue.isRefetching || today.isRefetching} onRefresh={() => { void catalogue.refetch(); void today.refetch(); }}><Brand /><Heading eyebrow="YPTrain · exercise guide" title="Find your next exercise" detail="Browse upper and lower body exercises from the shared YPGym catalogue." />
    {today.isLoading ? <Busy label="Checking today's workout" /> : null}{today.isError ? <Message title="Workout unavailable" detail={errorMessage(today.error)} action="Retry" onAction={() => void today.refetch()} tone="error" /> : null}
    {today.data?.session ? <Card><Text style={textStyles.subheading}>{`Today's workout · ${today.data.gym_date}`}</Text>{today.data.session.exercises.map((exercise) => <View key={exercise.id}><Text style={textStyles.body}>{exercise.name}</Text><Text style={textStyles.muted}>{exercise.sets.map((set) => `${set.set_order}: ${set.reps} reps × ${set.weight} ${set.unit}`).join(' · ')}</Text></View>)}</Card> : today.data ? <Message title={today.data.eligible ? 'Ready to log' : 'Check-in required'} detail={today.data.eligible ? 'Open an exercise to add it to today’s workout.' : today.data.reason ?? ''} action="Check again" onAction={() => void today.refetch()} /> : null}
    <Field label="Search exercise or muscle" placeholder="Search exercises" value={search} onChangeText={(value) => { setSearch(value); setPage(1); }} />
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginVertical: 16 }}>{(['all', 'upper', 'lower'] as const).map((value) => <Pressable key={value} accessibilityRole="button" accessibilityState={{ selected: region === value }} onPress={() => { setRegion(value); setPage(1); }} style={({ pressed }) => ({ minHeight: 46, justifyContent: 'center', borderRadius: 14, paddingHorizontal: 16, borderWidth: 1, borderColor: region === value ? colors.primary : colors.border, backgroundColor: region === value ? colors.primary : colors.white, opacity: pressed ? 0.82 : 1 })}><Text style={{ color: region === value ? colors.white : colors.text, fontWeight: '800', textTransform: 'capitalize' }}>{value === 'all' ? 'All' : `${value} body`}</Text></Pressable>)}</View>
    <Text style={{ color: colors.text, fontWeight: '800', marginBottom: 8 }}>Muscle filter</Text><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>{(['', ...muscles] as const).map((value) => <Pressable key={value || 'all'} accessibilityRole="button" accessibilityState={{ selected: muscle === value }} onPress={() => { setMuscle(value); setPage(1); }} style={({ pressed }) => ({ minHeight: 40, justifyContent: 'center', borderRadius: 20, paddingHorizontal: 12, backgroundColor: muscle === value ? colors.primarySurface : colors.white, borderWidth: 1, borderColor: muscle === value ? colors.primary : colors.border, opacity: pressed ? 0.82 : 1 })}><Text style={{ color: colors.text, fontSize: 12, fontWeight: '700' }}>{value || 'All muscles'}</Text></Pressable>)}</View>
    {catalogue.isLoading ? <Busy label="Loading exercises" /> : null}
    {catalogue.isError ? <Message title="Exercises unavailable" detail={errorMessage(catalogue.error)} action="Retry" onAction={() => void catalogue.refetch()} tone="error" /> : null}
    {catalogue.data?.items.length === 0 ? <Message title="No exercises match" detail="Try another search, body region or muscle." /> : null}
    {(['upper', 'lower'] as const).map((section) => { const rows = catalogue.data?.items.filter((item) => item.region === section) ?? []; return rows.length ? <View key={section} style={{ marginTop: 18 }}><Text style={[textStyles.subheading, { textTransform: 'capitalize', marginBottom: 10 }]}>{section} body</Text>{rows.map((item) => <ExerciseCard key={item.id} item={item} />)}</View> : null; })}
    {catalogue.data && catalogue.data.page.pages > 1 ? <View style={{ gap: 8, marginTop: 12 }}><Text style={textStyles.muted}>Page {page} of {catalogue.data.page.pages}</Text><View style={{ flexDirection: 'row', gap: 8 }}><View style={{ flex: 1 }}><Action label="Previous" outline disabled={page <= 1} onPress={() => setPage(page - 1)} /></View><View style={{ flex: 1 }}><Action label="Next" outline disabled={page >= catalogue.data.page.pages} onPress={() => setPage(page + 1)} /></View></View></View> : null}
    <Text style={[textStyles.muted, { marginTop: 16 }]}>Illustrative machine entries do not confirm what is installed at YPGym.</Text>
  </Screen>;
}

function ExerciseCard({ item }: { item: Exercise }) {
  return <Pressable accessibilityRole="button" accessibilityLabel={`View ${item.name} exercise guide`} onPress={() => router.push({ pathname: '/(member)/train/[id]', params: { id: item.id } })} style={({ pressed }) => ({ opacity: pressed ? 0.85 : 1 })}><Card><View style={{ height: 130, backgroundColor: colors.primarySurface, borderRadius: 12, justifyContent: 'center', alignItems: 'center', overflow: 'hidden' }}>{item.has_image ? <Image source={{ uri: apiUrl(exerciseImage(item)) }} style={{ width: '100%', height: '100%' }} resizeMode="cover" accessibilityLabel={`${item.name} exercise guide image`} /> : <Ionicons name="barbell-outline" size={54} color={colors.primary} />}</View><Text style={textStyles.subheading}>{item.name}</Text><Text style={textStyles.muted}>Primary: {item.primary_muscles.join(', ')}</Text>{item.is_illustrative ? <Text style={textStyles.muted}>Illustrative exercise</Text> : null}</Card></Pressable>;
}
