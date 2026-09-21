import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Alert, Pressable, Text, View } from 'react-native';

import { Action, Brand, Busy, Card, Field, Heading, Message, Pill, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatTime } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { queryClient } from '@/lib/query';
import { colors } from '@/lib/theme';
import type { Booking, ClassList, MemberClass, Waitlist } from '@/lib/types';

export default function ClassesScreen() {
  const { request, user } = useAuth();
  const [search, setSearch] = useState('');
  const [day, setDay] = useState<'all' | 'today' | 'tomorrow'>('all');
  const classes = useQuery({ queryKey: ['classes', user?.id], queryFn: ({ signal }) => request<ClassList>('/classes/upcoming', { signal }) });
  const change = useMutation({ mutationFn: ({ item, waitlist }: { item: MemberClass; waitlist: boolean }) => waitlist ? request<Booking | Waitlist>(`/classes/${item.id}/waitlist`, { method: 'POST' }) : request<Booking | Waitlist>(`/classes/${item.id}/book`, { method: 'POST' }),
    onSuccess: async (_, variables) => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['classes'] }), queryClient.invalidateQueries({ queryKey: ['dashboard'] }), queryClient.invalidateQueries({ queryKey: ['bookings'] })]); Alert.alert(variables.waitlist ? 'Waitlist joined' : 'Class booked', variables.item.title); },
    onError: (error) => Alert.alert('Could not update class', errorMessage(error)) });
  const visible = useMemo(() => (classes.data?.items ?? []).filter((item) => {
    const term = search.trim().toLowerCase();
    if (term && !`${item.title} ${item.class_type} ${item.trainer?.display_name ?? ''}`.toLowerCase().includes(term)) return false;
    if (day === 'all') return true;
    const target = new Date(); if (day === 'tomorrow') target.setDate(target.getDate() + 1);
    return new Date(item.start_at).toDateString() === target.toDateString();
  }), [classes.data, day, search]);

  function confirm(item: MemberClass, waitlist: boolean) {
    Alert.alert(waitlist ? 'Join waitlist?' : 'Book this class?', `${item.title} · ${formatDate(item.start_at)} ${formatTime(item.start_at)}`, [
      { text: 'Keep unchanged', style: 'cancel' },
      { text: 'Confirm', onPress: () => change.mutate({ item, waitlist }) },
    ]);
  }
  return <Screen refreshing={classes.isRefetching} onRefresh={() => void classes.refetch()}><Brand /><Heading title="Find a Class" detail="Live places, trainers and your booking state." />
    <Field label="Search by class or instructor" placeholder="Search classes" value={search} onChangeText={setSearch} />
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginVertical: 17 }}>{(['all', 'today', 'tomorrow'] as const).map((value) => <Pressable key={value} accessibilityRole="button" accessibilityState={{ selected: day === value }} onPress={() => setDay(value)} style={({ pressed }) => ({ minHeight: 46, justifyContent: 'center', backgroundColor: day === value ? colors.primary : colors.white, borderColor: day === value ? colors.primary : colors.border, borderWidth: 1, borderRadius: 14, paddingHorizontal: 17, opacity: pressed ? 0.82 : 1 })}><Text style={{ color: day === value ? colors.white : colors.text, fontWeight: '800', textTransform: 'capitalize' }}>{value}</Text></Pressable>)}</View>
    <Action label="My bookings and waitlists" onPress={() => router.push('/(member)/bookings')} outline />
    {classes.isLoading ? <Busy label="Loading upcoming classes" /> : null}
    {classes.isError ? <Message title="Classes unavailable" detail={errorMessage(classes.error)} action="Retry" onAction={() => void classes.refetch()} tone="error" /> : null}
    {classes.data && !classes.data.booking_eligible ? <Message title="Booking unavailable" detail={classes.data.eligibility_reason ?? 'An active membership is required.'} action="View plans" onAction={() => router.push('/(member)/renew')} tone="error" /> : null}
    {classes.data && !visible.length ? <Message title="No classes match" detail="Change the search or day filter and try again." /> : null}
    <View style={{ marginTop: 20 }}>{visible.map((item) => <Card key={item.id} accent={item.member_state === 'booked'}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 10 }}><Text style={textStyles.accent}>{formatDate(item.start_at)} · {formatTime(item.start_at)}</Text><Text style={{ color: colors.text, fontWeight: '800' }}>{item.remaining_capacity} left</Text></View>
      <Text style={textStyles.subheading}>{item.title}</Text><Text style={textStyles.muted}>{item.class_type} · {item.trainer?.display_name ?? 'Trainer pending'} · {item.location}</Text>
      {item.member_state === 'booked' ? <Pill label="Joined" /> : item.member_state === 'waitlisted' ? <Pill label={`Waitlisted · position ${item.waitlist_position ?? '—'}`} tone="warning" /> : item.member_state === 'full' ? <Action label="Join waitlist" outline disabled={!classes.data?.booking_eligible || change.isPending} onPress={() => confirm(item, true)} /> : <Action label={item.member_state === 'available' ? 'Book now' : 'Unavailable'} disabled={item.member_state !== 'available' || !classes.data?.booking_eligible || change.isPending} onPress={() => confirm(item, false)} />}
    </Card>)}</View>
  </Screen>;
}
