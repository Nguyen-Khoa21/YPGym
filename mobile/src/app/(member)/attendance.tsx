import { useQuery } from '@tanstack/react-query';
import { Text, View } from 'react-native';

import { Busy, Card, Heading, Message, PageTop, Pill, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatTime } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { AttendanceHistory } from '@/lib/types';

export default function AttendanceScreen() {
  const { request, user } = useAuth();
  const history = useQuery({ queryKey: ['attendance', user?.id], queryFn: ({ signal }) => request<AttendanceHistory>('/attendance/me?page=1&page_size=20', { signal }) });
  return <Screen refreshing={history.isRefetching} onRefresh={() => void history.refetch()}><PageTop title="Attendance" fallback="/(member)/(tabs)/qr" /><Heading title="Recent visits" detail="Visits confirmed by the gym scanner." />
    {history.isLoading ? <Busy label="Loading visits" /> : null}{history.isError ? <Message title="History unavailable" detail={errorMessage(history.error)} action="Retry" onAction={() => void history.refetch()} tone="error" /> : null}
    {history.data ? <Card accent><Text style={textStyles.subheading}>{history.data.distinct_visit_days.length} days visited</Text><Text style={textStyles.muted}>Counted by calendar day in {history.data.gym_timezone}.</Text>{history.data.distinct_visit_days.length ? <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{history.data.distinct_visit_days.slice(0, 12).map((day) => <Pill key={day} label={formatDate(day)} tone="positive" />)}</View> : null}</Card> : null}
    {history.data?.items.length === 0 ? <Message title="No visits yet" detail="Your first scanner check-in will appear here." /> : null}
    {history.data?.items.map((item) => <Card key={item.id}><Pill label={item.status.replaceAll('_', ' ')} tone={item.status === 'checked_in' ? 'warning' : 'positive'} /><Text style={textStyles.subheading}>{formatDate(item.checked_in_at)} · {formatTime(item.checked_in_at)}</Text><Text style={textStyles.muted}>Entry source: {item.source}</Text>{item.closed_at ? <Text style={textStyles.muted}>Checked out {formatTime(item.closed_at)}</Text> : null}</Card>)}
  </Screen>;
}
