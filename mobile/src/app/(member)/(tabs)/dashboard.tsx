import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import { Action, Brand, Busy, Card, Heading, Message, Pill, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatTime } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';
import type { Dashboard } from '@/lib/types';

export default function DashboardScreen() {
  const { request, user } = useAuth();
  const dashboard = useQuery({ queryKey: ['dashboard', user?.id], queryFn: ({ signal }) => request<Dashboard>('/dashboard/me', { signal }), refetchInterval: 30_000 });
  const data = dashboard.data;
  return <Screen refreshing={dashboard.isRefetching} onRefresh={() => void dashboard.refetch()}>
    <Brand right={<Pressable accessibilityRole="button" accessibilityLabel="Notifications" onPress={() => router.push('/(member)/notifications')}><Ionicons name="notifications-outline" size={23} color={colors.lime} /></Pressable>} />
    <Heading title="Member Dashboard" detail={`Welcome back, ${user?.name.split(' ')[0] ?? 'member'}. Let's hit it.`} />
    {dashboard.isLoading ? <Busy label="Loading your live account" /> : null}
    {dashboard.isError ? <Message title="Dashboard unavailable" detail={errorMessage(dashboard.error)} action="Retry" onAction={() => void dashboard.refetch()} /> : null}
    {data ? <>
      <Card accent><Pill label={`${data.membership?.status ?? 'No plan'} · ${data.member.tier}`} /><Text style={textStyles.muted}>Days Remaining</Text><Text style={{ color: colors.text, fontSize: 52, fontWeight: '900' }}>{data.membership?.days_remaining ?? '—'}</Text><Text style={textStyles.muted}>{data.membership ? `${data.membership.plan_name} · Expires ${formatDate(data.membership.expiry_date)}` : 'Choose a membership to unlock the gym.'}</Text><Action label={data.membership ? 'Renew membership →' : 'Choose a plan →'} onPress={() => router.push('/(member)/renew')} /></Card>
      <View style={{ flexDirection: 'row', gap: 12 }}>
        <View style={{ flex: 1 }}><Card><Ionicons name="qr-code-outline" size={27} color={colors.lime} /><Text style={textStyles.subheading}>Show QR</Text><Action label={data.qr_access.eligible ? 'Open pass' : 'Restricted'} disabled={!data.qr_access.eligible} onPress={() => router.push('/(member)/(tabs)/qr')} outline /></Card></View>
        <View style={{ flex: 1 }}><Card><Ionicons name="people-outline" size={26} color={colors.lime} /><Text style={textStyles.muted}>Live Capacity</Text><Text style={textStyles.subheading}>{data.crowdedness.percentage}%</Text><Pill label={data.crowdedness.status} tone={data.crowdedness.percentage > 80 ? 'coral' : 'lime'} /></Card></View>
      </View>
      {!data.qr_access.eligible && data.qr_access.reason ? <Text style={[textStyles.muted, { marginBottom: 15 }]}>{data.qr_access.reason}</Text> : null}
      {data.active_broadcasts.map((item) => <Card key={item.id} accent><Text style={textStyles.eyebrow}>Announcement</Text><Text style={textStyles.subheading}>{item.title}</Text><Text style={textStyles.muted}>{item.message}</Text></Card>)}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 22, marginBottom: 12 }}><Text style={textStyles.subheading}>Upcoming Classes</Text><Pressable accessibilityRole="button" onPress={() => router.push('/(member)/(tabs)/classes')}><Text style={textStyles.lime}>See All</Text></Pressable></View>
      {data.upcoming_bookings.length ? data.upcoming_bookings.map((booking) => <Card key={booking.id}><Text style={textStyles.lime}>{formatDate(booking.gym_class.start_at)}, {formatTime(booking.gym_class.start_at)}</Text><Text style={textStyles.subheading}>{booking.gym_class.title}</Text><Text style={textStyles.muted}>{booking.gym_class.trainer?.display_name ?? 'Trainer pending'} · {booking.gym_class.location}</Text></Card>) : <Message title="No upcoming classes" detail="Browse the schedule and book your next session." action="Find a class" onAction={() => router.push('/(member)/(tabs)/classes')} />}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 22, marginBottom: 12 }}><Text style={textStyles.subheading}>Notifications</Text><Pressable accessibilityRole="button" onPress={() => router.push('/(member)/notifications')}><Text style={textStyles.lime}>{data.unread_notification_count} unread</Text></Pressable></View>
      {data.recent_notifications.length ? data.recent_notifications.map((item) => <Card key={item.id}><Text style={textStyles.body}>{item.title}</Text><Text style={textStyles.muted}>{item.message}</Text></Card>) : <Text style={textStyles.muted}>No new notifications.</Text>}
    </> : null}
  </Screen>;
}
