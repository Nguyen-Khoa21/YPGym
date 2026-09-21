import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Alert, Pressable, Text, View } from 'react-native';

import { Brand, Busy, Card, Message, Pill, Screen, textStyles } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';
import type { Dashboard, User } from '@/lib/types';

function MenuRow({ icon, label, detail, onPress }: { icon: keyof typeof Ionicons.glyphMap; label: string; detail?: string; onPress: () => void }) {
  return <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={{ backgroundColor: colors.card, borderColor: colors.border, borderWidth: 1, borderRadius: 12, marginBottom: 11, minHeight: 76, paddingHorizontal: 17, flexDirection: 'row', alignItems: 'center', gap: 15 }}>
    <Ionicons name={icon} size={22} color={colors.lime} /><View style={{ flex: 1 }}><Text style={textStyles.body}>{label}</Text>{detail ? <Text style={textStyles.muted}>{detail}</Text> : null}</View><Ionicons name="chevron-forward" size={20} color={colors.muted} />
  </Pressable>;
}

export default function ProfileScreen() {
  const { request, user, logout } = useAuth();
  const profile = useQuery({ queryKey: ['profile', user?.id], queryFn: ({ signal }) => request<User>('/users/me', { signal }) });
  const dashboard = useQuery({ queryKey: ['dashboard', user?.id], queryFn: ({ signal }) => request<Dashboard>('/dashboard/me', { signal }), staleTime: 0, refetchOnMount: 'always' });
  function confirmLogout() { Alert.alert('Log out?', 'Your saved member session will be removed from this device.', [{ text: 'Stay signed in', style: 'cancel' }, { text: 'Log out', style: 'destructive', onPress: () => void logout() }]); }
  return <Screen refreshing={profile.isRefetching || dashboard.isRefetching} onRefresh={() => { void profile.refetch(); void dashboard.refetch(); }}><Brand /><View style={{ alignItems: 'center', gap: 12, marginVertical: 12 }}><View style={{ width: 96, height: 96, backgroundColor: colors.card, borderRadius: 28, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: colors.lime }}><Text style={{ color: colors.lime, fontSize: 40, fontWeight: '900' }}>{user?.name.slice(0, 1).toUpperCase()}</Text></View><Text style={textStyles.heading}>{user?.name}</Text><Pill label={dashboard.data?.membership?.status ?? 'No membership'} tone={dashboard.data?.qr_access.eligible ? 'lime' : 'coral'} centered /><Text style={textStyles.muted}>Account tier: {user?.tier.toUpperCase() ?? 'MEMBER'}</Text></View>
    {profile.isLoading ? <Busy label="Loading profile" /> : null}{profile.isError ? <Message title="Profile unavailable" detail={errorMessage(profile.error)} action="Retry" onAction={() => void profile.refetch()} /> : null}
    <View style={{ marginTop: 20 }}><MenuRow icon="person-outline" label="Personal Information" detail={profile.data?.email ?? ''} onPress={() => router.push('/(member)/profile-edit')} />
      <MenuRow icon="card-outline" label="Membership Plan" detail={dashboard.data?.membership ? `${dashboard.data.membership.plan_name} · ${dashboard.data.membership.status}` : 'Choose a plan'} onPress={() => router.push('/(member)/renew')} />
      <MenuRow icon="receipt-outline" label="Invoices" detail="Verified mock-payment history" onPress={() => router.push('/(member)/invoices')} />
      <MenuRow icon="notifications-outline" label="Notification Preferences" onPress={() => router.push('/(member)/preferences')} />
      <MenuRow icon="calendar-outline" label="My Bookings" onPress={() => router.push('/(member)/bookings')} /></View>
    <Card><Pressable accessibilityRole="button" onPress={confirmLogout} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, minHeight: 40 }}><Ionicons name="log-out-outline" color={colors.coral} size={22} /><Text style={{ color: colors.coral, fontSize: 18, fontWeight: '800' }}>Log Out</Text></Pressable></Card>
  </Screen>;
}
