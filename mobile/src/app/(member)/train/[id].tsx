import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { Image, Text, View } from 'react-native';

import { Action, Busy, Card, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { apiUrl, errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';
import { exerciseImage, type Exercise } from '@/lib/training';

export default function ExerciseDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { request, user } = useAuth();
  const exercise = useQuery({ queryKey: ['training', 'exercise', user?.id, id], queryFn: ({ signal }) => request<Exercise>(`/training/exercises/${id}`, { signal }), enabled: !!id });
  return <Screen><PageTop title="Exercise guide" fallback="/(member)/(tabs)/train" />
    {exercise.isLoading ? <Busy label="Loading exercise" /> : null}
    {exercise.isError ? <Message title="Exercise unavailable" detail={errorMessage(exercise.error)} action="Retry" onAction={() => void exercise.refetch()} tone="error" /> : null}
    {exercise.data ? <><View style={{ height: 220, borderRadius: 18, backgroundColor: colors.primarySurface, alignItems: 'center', justifyContent: 'center', overflow: 'hidden', marginBottom: 16 }}>{exercise.data.has_image ? <Image source={{ uri: apiUrl(exerciseImage(exercise.data)) }} style={{ width: '100%', height: '100%' }} resizeMode="cover" accessibilityLabel={`${exercise.data.name} exercise guide image`} /> : <Ionicons name="barbell-outline" size={70} color={colors.primary} />}</View>
      <Text style={textStyles.accent}>{exercise.data.region.toUpperCase()} BODY · YPTRAIN</Text><Text style={[textStyles.subheading, { fontSize: 30, marginTop: 8 }]}>{exercise.data.name}</Text><Text style={[textStyles.muted, { marginVertical: 12 }]}>{exercise.data.description}</Text>
      {exercise.data.is_illustrative ? <Message title="Illustrative guide" detail="Confirm on-site equipment availability where applicable." /> : null}
      <Card><Text style={textStyles.subheading}>How to use</Text><Text style={textStyles.body}>{exercise.data.usage_steps}</Text></Card>
      <Card><Text style={textStyles.subheading}>Muscles</Text><Text style={textStyles.body}>Primary: {exercise.data.primary_muscles.join(', ')}</Text><Text style={textStyles.body}>Secondary: {exercise.data.secondary_muscles.join(', ') || 'None listed'}</Text></Card>
      <Card><Text style={textStyles.subheading}>Safety note</Text><Text style={textStyles.body}>{exercise.data.safety_note}</Text></Card>
      <Action label="Add Exercise · coming soon" onPress={() => {}} disabled /><Text style={[textStyles.muted, { marginTop: 8 }]}>Workout logging arrives in the next YPTrain update and will require a verified gym check-in.</Text>
    </> : null}
  </Screen>;
}
