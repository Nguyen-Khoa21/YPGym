import { useMutation, useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Alert, Text, View } from 'react-native';

import { Action, Busy, Card, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatTime } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { queryClient } from '@/lib/query';
import type { Booking, Bookings, Waitlist } from '@/lib/types';

export default function BookingsScreen() {
  const { request, user } = useAuth();
  const bookings = useQuery({ queryKey: ['bookings', user?.id], queryFn: ({ signal }) => request<Bookings>('/bookings/me', { signal }) });
  const change = useMutation({ mutationFn: ({ id, leave }: { id: string; leave: boolean }) => leave ? request<Booking | Waitlist>(`/classes/${id}/waitlist`, { method: 'DELETE' }) : request<Booking | Waitlist>(`/bookings/${id}/cancel`, { method: 'POST' }),
    onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['bookings'] }), queryClient.invalidateQueries({ queryKey: ['classes'] }), queryClient.invalidateQueries({ queryKey: ['dashboard'] })]); },
    onError: (error) => Alert.alert('Could not update booking', errorMessage(error)) });
  function confirm(id: string, title: string, leave: boolean) { Alert.alert(leave ? 'Leave waitlist?' : 'Cancel booking?', `${title}. A cancelled place may be offered to another member.`, [{ text: 'Keep unchanged', style: 'cancel' }, { text: 'Confirm', style: 'destructive', onPress: () => change.mutate({ id, leave }) }]); }
  return <Screen refreshing={bookings.isRefetching} onRefresh={() => void bookings.refetch()}><PageTop title="My Bookings" fallback="/(member)/(tabs)/classes" /><Heading title="Your class queue" detail={bookings.data ? `Cancellations close ${bookings.data.cancellation_window_hours} hours before class start.` : undefined} />
    {bookings.isLoading ? <Busy label="Loading your bookings" /> : null}{bookings.isError ? <Message title="Bookings unavailable" detail={errorMessage(bookings.error)} action="Retry" onAction={() => void bookings.refetch()} /> : null}
    {bookings.data && !bookings.data.bookings.length && !bookings.data.waitlists.length ? <Message title="No bookings yet" detail="Find an upcoming class and reserve your place." action="Browse classes" onAction={() => router.push('/(member)/(tabs)/classes')} /> : null}
    {bookings.data?.bookings.length ? <><Text style={[textStyles.subheading, { marginBottom: 12 }]}>Bookings</Text>{bookings.data.bookings.map((entry) => <Card key={entry.id}><Text style={textStyles.subheading}>{entry.gym_class.title}</Text><Text style={textStyles.muted}>{formatDate(entry.gym_class.start_at)} · {formatTime(entry.gym_class.start_at)} · {entry.gym_class.location}</Text><Text style={textStyles.lime}>{entry.status.toUpperCase()}</Text>{entry.status === 'booked' && entry.can_cancel ? <Action label="Cancel booking" outline danger disabled={change.isPending} onPress={() => confirm(entry.id, entry.gym_class.title, false)} /> : null}</Card>)}</> : null}
    {bookings.data?.waitlists.length ? <View style={{ marginTop: 22 }}><Text style={[textStyles.subheading, { marginBottom: 12 }]}>Waitlists</Text>{bookings.data.waitlists.map((entry) => <Card key={entry.id}><Text style={textStyles.subheading}>{entry.gym_class.title}</Text><Text style={textStyles.muted}>{formatDate(entry.gym_class.start_at)} · Position {entry.position}</Text><Text style={textStyles.lime}>{entry.status.toUpperCase()}</Text>{entry.status === 'waiting' ? <Action label="Leave waitlist" outline disabled={change.isPending} onPress={() => confirm(entry.gym_class.id, entry.gym_class.title, true)} /> : null}</Card>)}</View> : null}
  </Screen>;
}
