import { useQuery } from '@tanstack/react-query';
import { Text } from 'react-native';

import { Busy, Card, Heading, Message, PageTop, Pill, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatTime } from '@/lib/api';
import { useAuth } from '@/lib/auth';

type Attendance = { items: { id: string; checked_in_at: string; closed_at: string | null; status: string; source: string }[] };

export default function AttendanceScreen() {
  const { request, user } = useAuth();
  const history = useQuery({ queryKey: ['attendance', user?.id], queryFn: ({ signal }) => request<Attendance>('/attendance/me?page=1&page_size=20', { signal }) });
  return <Screen refreshing={history.isRefetching} onRefresh={() => void history.refetch()}><PageTop title="Attendance" fallback="/(member)/(tabs)/qr" /><Heading title="Recent visits" detail="Visits confirmed by the gym scanner." />
    {history.isLoading ? <Busy label="Loading visits" /> : null}{history.isError ? <Message title="History unavailable" detail={errorMessage(history.error)} action="Retry" onAction={() => void history.refetch()} tone="error" /> : null}
    {history.data?.items.length === 0 ? <Message title="No visits yet" detail="Your first scanner check-in will appear here." /> : null}
    {history.data?.items.map((item) => <Card key={item.id}><Pill label={item.status.replaceAll('_', ' ')} tone={item.status === 'checked_in' ? 'warning' : 'positive'} /><Text style={textStyles.subheading}>{formatDate(item.checked_in_at)} · {formatTime(item.checked_in_at)}</Text><Text style={textStyles.muted}>Entry source: {item.source}</Text>{item.closed_at ? <Text style={textStyles.muted}>Checked out {formatTime(item.closed_at)}</Text> : null}</Card>)}
  </Screen>;
}
