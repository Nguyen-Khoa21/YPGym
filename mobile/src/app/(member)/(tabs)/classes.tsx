import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import * as WebBrowser from 'expo-web-browser';
import { router, type Href } from 'expo-router';
import { Alert, Platform, Pressable, Text, View } from 'react-native';

import { Action, Brand, Busy, Card, Field, Heading, Message, Pill, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatMoney, formatTime } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { queryClient } from '@/lib/query';
import { colors } from '@/lib/theme';
import type { ClassCheckoutResponse, ClassList, MemberClass, Waitlist } from '@/lib/types';

export default function ClassesScreen() {
  const { request, user } = useAuth();
  const [search, setSearch] = useState('');
  const [day, setDay] = useState<'all' | 'today' | 'tomorrow'>('all');
  const classes = useQuery({ queryKey: ['classes', user?.id], queryFn: ({ signal }) => request<ClassList>('/classes/upcoming', { signal }) });
  const change = useMutation<Waitlist | ClassCheckoutResponse, Error, { item: MemberClass; waitlist: boolean }>({ mutationFn: ({ item, waitlist }) => waitlist ? request<Waitlist>(`/classes/${item.id}/waitlist`, { method: 'POST' }) : request<ClassCheckoutResponse>(`/classes/${item.id}/checkout`, { method: 'POST', body: { idempotency_key: `${Date.now()}-${Math.random().toString(36).slice(2)}`, locale: 'vn', bank_code: null, client_platform: Platform.OS === 'web' ? 'mobile_web' : 'mobile' } }),
    onSuccess: async (result, variables) => { if (variables.waitlist) { await Promise.all([queryClient.invalidateQueries({ queryKey: ['classes'] }), queryClient.invalidateQueries({ queryKey: ['bookings'] })]); Alert.alert('Waitlist joined', variables.item.title); return; } const payment = result as ClassCheckoutResponse; router.push(`/payment-result?transaction_id=${encodeURIComponent(payment.transaction_id)}&state=processing` as Href); if (Platform.OS === 'web') window.location.assign(payment.payment_url); else await WebBrowser.openBrowserAsync(payment.payment_url); },
    onError: (error) => Alert.alert('Could not update class', errorMessage(error)) });
  const visible = useMemo(() => (classes.data?.items ?? []).filter((item) => {
    const term = search.trim().toLowerCase();
    if (term && !`${item.title} ${item.class_type} ${item.trainer?.display_name ?? ''}`.toLowerCase().includes(term)) return false;
    if (day === 'all') return true;
    const target = new Date(); if (day === 'tomorrow') target.setDate(target.getDate() + 1);
    return new Date(item.start_at).toDateString() === target.toDateString();
  }), [classes.data, day, search]);

  function confirm(item: MemberClass, waitlist: boolean) {
    Alert.alert(waitlist ? 'Join waitlist?' : 'Book & pay for this class?', `${item.title} · ${formatDate(item.start_at)} ${formatTime(item.start_at)}\n${item.price_vnd ? formatMoney(item.price_vnd) : 'Price unavailable'}\n\nOne payment reserves one seat. Cancellation before the session requires staff refund resolution.`, [
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
    {classes.data && !classes.data.booking_eligible ? <Message title="Booking unavailable" detail={classes.data.eligibility_reason ?? 'Verify your email before purchasing a class.'} tone="error" /> : null}
    {classes.data && !visible.length ? <Message title="No classes match" detail="Change the search or day filter and try again." /> : null}
    <View style={{ marginTop: 20 }}>{visible.map((item) => <Card key={item.id} accent={item.member_state === 'confirmed'}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 10 }}><Text style={textStyles.accent}>{formatDate(item.start_at)} · {formatTime(item.start_at)}</Text><Text style={{ color: colors.text, fontWeight: '800' }}>{item.remaining_capacity} left</Text></View>
      <Text style={textStyles.subheading}>{item.title}</Text><Text style={textStyles.muted}>{item.class_type} · {item.trainer?.display_name ?? 'Trainer pending'} · {item.location}</Text><Text style={{ color: colors.primary, fontSize: 25, fontWeight: '900' }}>{item.price_vnd ? formatMoney(item.price_vnd) : 'Price pending'}</Text>
      {item.member_state === 'confirmed' ? <Pill label="Booked" tone="positive" /> : item.member_state === 'pending_payment' ? <Pill label="Payment pending" tone="warning" /> : item.member_state === 'waitlisted' ? <Pill label={`Waitlisted · position ${item.waitlist_position ?? '—'}`} tone="warning" /> : item.member_state === 'full' ? <Action label="Join waitlist" outline disabled={!classes.data?.booking_eligible || change.isPending} onPress={() => confirm(item, true)} /> : <Action label={item.member_state === 'available' ? 'Book & pay' : 'Unavailable'} disabled={item.member_state !== 'available' || !classes.data?.booking_eligible || change.isPending} onPress={() => confirm(item, false)} />}
    </Card>)}</View>
  </Screen>;
}
