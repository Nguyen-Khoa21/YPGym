import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router, type Href } from 'expo-router';
import { useEffect } from 'react';
import { Text, View, useWindowDimensions } from 'react-native';

import { ExpiredMembershipPanel } from '@/components/ExpiredMembershipPanel';
import { Action, Brand, Busy, Card, Heading, IconButton, Message, Pill, Screen, SectionTitle, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatTime } from '@/lib/api';
import { badgeText, bellLabel } from '@/lib/badge';
import { useAuth } from '@/lib/auth';
import { shouldPromptOnboarding, type OnboardingState, type Recommendations } from '@/lib/onboarding';
import { colors } from '@/lib/theme';
import type { Dashboard } from '@/lib/types';

let onboardingPrompted = false;

export default function DashboardScreen() {
  const { request, user } = useAuth();
  const { width } = useWindowDimensions();
  const dashboard = useQuery({ queryKey: ['dashboard', user?.id], queryFn: ({ signal }) => request<Dashboard>('/dashboard/me', { signal }), staleTime: 0, refetchOnMount: 'always', refetchInterval: 30_000 });
  const onboarding = useQuery({ queryKey: ['onboarding', user?.id], queryFn: ({ signal }) => request<OnboardingState>('/users/me/onboarding', { signal }) });
  const recommendations = useQuery({ queryKey: ['recommendations', user?.id], staleTime: 300_000, queryFn: ({ signal }) => request<Recommendations>('/users/me/recommendations', { signal }) });
  const onboardingStatus = onboarding.data?.status;
  useEffect(() => {
    // Ask once right after the first login; answering or skipping is stored on the server.
    if (!shouldPromptOnboarding(onboardingStatus, onboardingPrompted)) return;
    onboardingPrompted = true;
    router.push('/(member)/onboarding' as Href);
  }, [onboardingStatus]);
  const data = dashboard.data;
  return <Screen refreshing={dashboard.isRefetching} onRefresh={() => void dashboard.refetch()}>
    <Brand right={<IconButton icon="notifications-outline" label={bellLabel(data?.unread_notification_count)} badge={badgeText(data?.unread_notification_count)} onPress={() => router.push('/(member)/notifications')} />} />
    <Heading eyebrow="Today's training" title="Member Dashboard" detail={`Welcome back, ${user?.name.split(' ')[0] ?? 'member'}. Let's hit it.`} />
    {dashboard.isLoading ? <Busy label="Loading your live account" /> : null}
    {dashboard.isError ? <Message title="Dashboard unavailable" detail={errorMessage(dashboard.error)} action="Retry" onAction={() => void dashboard.refetch()} tone="error" /> : null}
    {data ? <>
      <Card accent style={{ gap: 6 }}>
        <Text style={textStyles.eyebrow}>Live capacity</Text>
        {data.crowdedness ? <>
          <Text style={[textStyles.subheading, { fontSize: 22 }]}>{data.crowdedness.gym_name}</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}><Text style={{ color: colors.primary, fontSize: 46, lineHeight: 50, fontWeight: '900' }}>{data.crowdedness.percentage}%</Text><Pill label={data.crowdedness.status} tone={data.crowdedness.percentage > 80 ? 'danger' : 'positive'} /></View>
          <View accessibilityRole="progressbar" accessibilityLabel="Capacity used" accessibilityValue={{ min: 0, max: 100, now: Math.min(100, Math.max(0, data.crowdedness.percentage)) }} style={{ height: 10, borderRadius: 5, backgroundColor: colors.surfaceStrong, overflow: 'hidden' }}><View style={{ width: `${Math.min(100, Math.max(0, data.crowdedness.percentage))}%`, height: '100%', backgroundColor: colors.positive }} /></View>
          <Text style={textStyles.muted}>{data.crowdedness.active_count} of {data.crowdedness.capacity} places in use right now.</Text>
        </> : <>
          <Text style={textStyles.subheading}>{data.membership ? data.membership.home_gym_name : 'Choose your gym'}</Text>
          <Text style={textStyles.muted}>{data.membership ? 'Live capacity is not available right now.' : 'Buy a membership and pick a location to see live capacity and your check-in code.'}</Text>
        </>}
      </Card>
      <View style={{ flexDirection: width < 390 ? 'column' : 'row', gap: 12 }}>
        <View style={{ flex: 1 }}><Card style={{ flex: 1, minHeight: 176 }}><Ionicons name="qr-code-outline" size={27} color={colors.primary} /><Text style={textStyles.subheading}>Show QR</Text><Text style={textStyles.muted}>{data.qr_access.eligible ? 'Ready for check-in.' : 'Not available right now.'}</Text><Action label={data.qr_access.eligible ? 'Open pass' : 'Restricted'} disabled={!data.qr_access.eligible} onPress={() => router.push('/(member)/(tabs)/qr')} outline /></Card></View>
        <View style={{ flex: 1 }}><Card style={{ flex: 1, minHeight: 176 }} accent><Pill label={data.membership?.status ?? 'No membership'} tone={data.qr_access.eligible ? 'positive' : 'danger'} /><Text style={textStyles.subheading}>{data.membership ? `${data.membership.days_remaining} days left` : 'No plan yet'}</Text><Text style={textStyles.muted}>{data.membership ? `Expires ${formatDate(data.membership.expiry_date)}` : 'Choose a membership to unlock the gym.'}</Text><Text style={[textStyles.muted, { fontSize: 12 }]}>Tier: {data.member.tier.toUpperCase()}</Text><Action label={data.membership ? 'Manage' : 'Choose a plan'} onPress={() => router.push('/(member)/renew')} outline /></Card></View>
      </View>
      {!data.qr_access.eligible && data.qr_access.reason ? <Text style={[textStyles.muted, { marginBottom: 15 }]}>{data.qr_access.reason}</Text> : null}
      <ExpiredMembershipPanel membership={data.membership} />
      <SectionTitle title="Upcoming Classes" action="See all" onAction={() => router.push('/(member)/(tabs)/classes')} />
      {data.upcoming_bookings.length ? data.upcoming_bookings.slice(0, 2).map((booking) => <Card key={booking.id}><Text style={textStyles.accent}>{formatDate(booking.gym_class.start_at)}, {formatTime(booking.gym_class.start_at)}</Text><Text style={textStyles.subheading}>{booking.gym_class.title}</Text><Text style={textStyles.muted}>{booking.gym_class.trainer?.display_name ?? 'Trainer pending'} · {booking.gym_class.location}</Text></Card>) : <Message title="No upcoming classes" detail="Browse the schedule and book your next session." action="Find a class" onAction={() => router.push('/(member)/(tabs)/classes')} />}
      {recommendations.data?.quiet_hours ? <Card><Text style={textStyles.eyebrow}>Quiet time for you</Text><Text style={textStyles.subheading}>{recommendations.data.quiet_hours.label}</Text><Text style={textStyles.muted}>at {recommendations.data.quiet_hours.gym_name}, based on last month's attendance.</Text></Card> : recommendations.data?.quiet_hours_reason ? <Card><Text style={textStyles.muted}>Not enough attendance data yet to suggest a quiet time.</Text></Card> : null}
      {data.active_broadcasts.map((item) => <Card key={item.id} accent><Text style={textStyles.eyebrow}>Announcement</Text><Text style={textStyles.subheading}>{item.title}</Text><Text style={textStyles.muted}>{item.message}</Text></Card>)}
      <SectionTitle title="Notifications" action={`${data.unread_notification_count} unread`} onAction={() => router.push('/(member)/notifications')} />
      {data.recent_notifications.length ? data.recent_notifications.map((item) => <Card key={item.id}><Text style={textStyles.body}>{item.title}</Text><Text style={textStyles.muted}>{item.message}</Text></Card>) : <Text style={textStyles.muted}>No new notifications.</Text>}
    </> : null}
  </Screen>;
}
