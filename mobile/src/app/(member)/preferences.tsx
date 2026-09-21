import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Alert, Switch, Text, View } from 'react-native';

import { Action, Busy, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { queryClient } from '@/lib/query';
import { colors } from '@/lib/theme';
import type { Preferences } from '@/lib/types';

const fields: { key: keyof Preferences; label: string }[] = [
  { key: 'email_enabled', label: 'Development email notices' }, { key: 'in_app_enabled', label: 'In-app notices' },
  { key: 'expiry_reminders_enabled', label: 'Membership reminders' }, { key: 'class_reminders_enabled', label: 'Booked class reminders' },
  { key: 'broadcasts_enabled', label: 'Gym announcements' },
];

export default function PreferencesScreen() {
  const { request, user } = useAuth();
  const query = useQuery({ queryKey: ['preferences', user?.id], queryFn: ({ signal }) => request<Preferences>('/notifications/preferences/me', { signal }) });
  const [overrides, setOverrides] = useState<Partial<Preferences>>({});
  const values = query.data ? { ...query.data, ...overrides } : null;
  const save = useMutation({ mutationFn: () => request<Preferences>('/notifications/preferences/me', { method: 'PATCH', body: values }), onSuccess: async () => { setOverrides({}); await Promise.all([queryClient.invalidateQueries({ queryKey: ['preferences'] }), queryClient.invalidateQueries({ queryKey: ['dashboard'] })]); Alert.alert('Preferences saved'); }, onError: (error) => Alert.alert('Could not save preferences', errorMessage(error)) });
  return <Screen><PageTop title="Notification Preferences" fallback="/(member)/(tabs)/profile" /><Heading title="Choose your updates" detail="These settings control the backend notification channels." />
    {query.isLoading ? <Busy label="Loading preferences" /> : null}{query.isError ? <Message title="Preferences unavailable" detail={errorMessage(query.error)} action="Retry" onAction={() => void query.refetch()} tone="error" /> : null}
    {values ? <View style={{ gap: 10 }}>{fields.map((field) => <View key={field.key} style={{ minHeight: 68, backgroundColor: colors.card, borderColor: colors.border, borderWidth: 1, borderRadius: 18, paddingHorizontal: 17, paddingVertical: 12, flexDirection: 'row', alignItems: 'center' }}><Text style={[textStyles.body, { flex: 1 }]}>{field.label}</Text><Switch accessibilityLabel={field.label} value={values[field.key]} onValueChange={(value) => setOverrides({ ...overrides, [field.key]: value })} trackColor={{ false: colors.surfaceStrong, true: colors.positive }} thumbColor={colors.white} /></View>)}<Action label={save.isPending ? 'Saving…' : 'Save preferences'} disabled={save.isPending} onPress={() => save.mutate()} /></View> : null}
  </Screen>;
}
