import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Text, View, useWindowDimensions } from 'react-native';

import { Action, Brand, Busy, Card, Heading, IconButton, Message, Pill, Screen, SectionTitle, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatTime } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';
import type { Dashboard } from '@/lib/types';

export default function DashboardScreen() {
  const { request, user } = useAuth();
  const { width } = useWindowDimensions();
  const dashboard = useQuery({ queryKey: ['dashboard', user?.id], queryFn: ({ signal }) => request<Dashboard>('/dashboard/me', { signal }), staleTime: 0, refetchOnMount: 'always', refetchInterval: 30_000 });
  const data = dashboard.data;
  return <Screen refreshing={dashboard.isRefetching} onRefresh={() => void dashboard.refetch()}>
    <Brand right={<IconButton icon="notifications-outline" label="Notifications" onPress={() => router.push('/(member)/notifications')} />} />
    <Heading eyebrow="Today's training" title="Member Dashboard" detail={`Welcome back, ${user?.name.split(' ')[0] ?? 'member'}. Let's hit it.`} />
    {dashboard.isLoading ? <Busy label="Loading your live account" /> : null}
    {dashboard.isError ? <Message title="Dashboard unavailable" detail={errorMessage(dashboard.error)} action="Retry" onAction={() => void dashboard.refetch()} tone="error" /> : null}
    {data ? <>
      <Card accent><Pill label={data.membership?.status ?? 'No membership'} tone={data.qr_access.eligible ? 'positive' : 'danger'} /><Text style={textStyles.muted}>Account tier: {data.member.tier.toUpperCase()}</Text><Text style={textStyles.eyebrow}>Days remaining</Text><Text style={{ color: colors.primary, fontSize: 54, lineHeight: 58, fontWeight: '900' }}>{data.membership?.days_remaining ?? '—'}</Text><Text style={textStyles.muted}>{data.membership ? `${data.membership.plan_name} · Expires ${formatDate(data.membership.expiry_date)}` : 'Choose a membership to unlock the gym.'}</Text>{data.membership && !data.qr_access.eligible ? <Text style={textStyles.muted}>{data.membership.message}</Text> : null}<Action label={data.membership ? 'View membership options →' : 'Choose a plan →'} onPress={() => router.push('/(member)/renew')} /></Card>
      <View style={{ flexDirection: width < 390 ? 'column' : 'row', gap: 12 }}>
        <View style={{ flex: 1 }}><Card><Ionicons name="qr-code-outline" size={27} color={colors.primary} /><Text style={textStyles.subheading}>Show QR</Text><Action label={data.qr_access.eligible ? 'Open pass' : 'Restricted'} disabled={!data.qr_access.eligible} onPress={() => router.push('/(member)/(tabs)/qr')} outline /></Card></View>
        <View style={{ flex: 1 }}><Card><Ionicons name="people-outline" size={26} color={colors.primary} /><Text style={textStyles.muted}>Live Capacity</Text><Text style={textStyles.subheading}>{data.crowdedness.percentage}%</Text><Pill label={data.crowdedness.status} tone={data.crowdedness.percentage > 80 ? 'danger' : 'positive'} /></Card></View>
      </View>
      {!data.qr_access.eligible && data.qr_access.reason ? <Text style={[textStyles.muted, { marginBottom: 15 }]}>{data.qr_access.reason}</Text> : null}
      {data.active_broadcasts.map((item) => <Card key={item.id} accent><Text style={textStyles.eyebrow}>Announcement</Text><Text style={textStyles.subheading}>{item.title}</Text><Text style={textStyles.muted}>{item.message}</Text></Card>)}
      <SectionTitle title="Upcoming Classes" action="See all" onAction={() => router.push('/(member)/(tabs)/classes')} />
      {data.upcoming_bookings.length ? data.upcoming_bookings.map((booking) => <Card key={booking.id}><Text style={textStyles.accent}>{formatDate(booking.gym_class.start_at)}, {formatTime(booking.gym_class.start_at)}</Text><Text style={textStyles.subheading}>{booking.gym_class.title}</Text><Text style={textStyles.muted}>{booking.gym_class.trainer?.display_name ?? 'Trainer pending'} · {booking.gym_class.location}</Text></Card>) : <Message title="No upcoming classes" detail="Browse the schedule and book your next session." action="Find a class" onAction={() => router.push('/(member)/(tabs)/classes')} />}
      <SectionTitle title="Notifications" action={`${data.unread_notification_count} unread`} onAction={() => router.push('/(member)/notifications')} />
      {data.recent_notifications.length ? data.recent_notifications.map((item) => <Card key={item.id}><Text style={textStyles.body}>{item.title}</Text><Text style={textStyles.muted}>{item.message}</Text></Card>) : <Text style={textStyles.muted}>No new notifications.</Text>}
    </> : null}
  </Screen>;
}
