import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router, type Href } from 'expo-router';
import { Alert, Pressable, Text, View } from 'react-native';

import { Brand, Busy, Card, Message, Pill, Screen, textStyles } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';
import type { Dashboard, User } from '@/lib/types';

function MenuRow({ icon, label, detail, onPress }: { icon: keyof typeof Ionicons.glyphMap; label: string; detail?: string; onPress: () => void }) {
  return <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={({ pressed }) => ({ backgroundColor: pressed ? colors.primarySurface : colors.card, borderColor: colors.border, borderWidth: 1, borderRadius: 18, marginBottom: 11, minHeight: 76, paddingHorizontal: 15, flexDirection: 'row', alignItems: 'center', gap: 13, transform: [{ scale: pressed ? 0.985 : 1 }] })}>
    <View style={{ width: 42, height: 42, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.primarySurface }}><Ionicons name={icon} size={22} color={colors.primary} /></View><View style={{ flex: 1 }}><Text style={textStyles.body}>{label}</Text>{detail ? <Text style={textStyles.muted}>{detail}</Text> : null}</View><Ionicons name="chevron-forward" size={20} color={colors.muted} />
  </Pressable>;
}

export default function ProfileScreen() {
  const { request, user, logout } = useAuth();
  const profile = useQuery({ queryKey: ['profile', user?.id], queryFn: ({ signal }) => request<User>('/users/me', { signal }) });
  const dashboard = useQuery({ queryKey: ['dashboard', user?.id], queryFn: ({ signal }) => request<Dashboard>('/dashboard/me', { signal }), staleTime: 0, refetchOnMount: 'always' });
  function confirmLogout() { Alert.alert('Log out?', 'Your saved member session will be removed from this device.', [{ text: 'Stay signed in', style: 'cancel' }, { text: 'Log out', style: 'destructive', onPress: () => void logout() }]); }
  return <Screen refreshing={profile.isRefetching || dashboard.isRefetching} onRefresh={() => { void profile.refetch(); void dashboard.refetch(); }}><Brand /><View style={{ alignItems: 'center', gap: 12, marginVertical: 12 }}><View style={{ width: 96, height: 96, backgroundColor: colors.primarySurface, borderRadius: 32, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: colors.positiveBorder }}><Text style={{ color: colors.primary, fontSize: 40, fontWeight: '900' }}>{user?.name.slice(0, 1).toUpperCase()}</Text></View><Text style={textStyles.heading}>{user?.name}</Text><Pill label={dashboard.data?.membership?.status ?? 'No membership'} tone={dashboard.data?.qr_access.eligible ? 'positive' : 'danger'} centered /><Text style={textStyles.muted}>Account tier: {user?.tier.toUpperCase() ?? 'MEMBER'}</Text></View>
    {profile.isLoading ? <Busy label="Loading profile" /> : null}{profile.isError ? <Message title="Profile unavailable" detail={errorMessage(profile.error)} action="Retry" onAction={() => void profile.refetch()} tone="error" /> : null}
    <View style={{ marginTop: 20 }}><MenuRow icon="person-outline" label="Personal Information" detail={profile.data?.email ?? ''} onPress={() => router.push('/(member)/profile-edit')} />
      <MenuRow icon="card-outline" label="Membership Plan" detail={dashboard.data?.membership ? `${dashboard.data.membership.plan_name} · ${dashboard.data.membership.status}` : 'Choose a plan'} onPress={() => router.push('/(member)/renew')} />
      <MenuRow icon="receipt-outline" label="Invoices" detail="Verified mock-payment history" onPress={() => router.push('/(member)/invoices')} />
      <MenuRow icon="notifications-outline" label="Notification Preferences" onPress={() => router.push('/(member)/preferences')} />
      <MenuRow icon="pause-circle-outline" label="Membership Requests" detail="Request a freeze or cancellation" onPress={() => router.push('/(member)/membership-requests' as Href)} />
      <MenuRow icon="calendar-outline" label="My Bookings" onPress={() => router.push('/(member)/bookings')} /></View>
    <Card><Pressable accessibilityRole="button" onPress={confirmLogout} style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, minHeight: 48, opacity: pressed ? 0.7 : 1 })}><Ionicons name="log-out-outline" color={colors.danger} size={22} /><Text style={{ color: colors.danger, fontSize: 17, fontWeight: '800' }}>Log Out</Text></Pressable></Card>
  </Screen>;
}
