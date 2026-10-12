import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Text } from 'react-native';

import { Action, Busy, Card, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatMoney } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { shouldPollPayment } from '@/lib/payment';
import { refreshMembershipQueryData } from '@/lib/query';
import type { PaymentStatus } from '@/lib/types';

export default function PaymentResultScreen() {
  const params = useLocalSearchParams<{ transaction_id?: string; state?: string }>();
  const { request } = useAuth();
  const [timedOutTransaction, setTimedOutTransaction] = useState<string | null>(null);
  const timedOut = timedOutTransaction === params.transaction_id;
  useEffect(() => {
    const timer = setTimeout(() => setTimedOutTransaction(params.transaction_id ?? null), 30_000);
    return () => clearTimeout(timer);
  }, [params.transaction_id]);
  const payment = useQuery({
    queryKey: ['payment', params.transaction_id],
    queryFn: ({ signal }) => request<PaymentStatus>(`/payments/${params.transaction_id}`, { signal }),
    enabled: Boolean(params.transaction_id && params.state !== 'invalid'),
    retry: false,
    refetchInterval: (query) => shouldPollPayment((query.state.data as PaymentStatus | undefined)?.status, timedOut) ? 2_000 : false,
  });

  if (!params.transaction_id || params.state === 'invalid') return <Screen><PageTop title="Payment Result" fallback="/(member)/renew" /><Message title="Payment response not verified" detail="Start a new VNPay checkout from the membership plans." action="Choose a plan" onAction={() => router.replace('/(member)/renew')} tone="error" /></Screen>;
  if (payment.isLoading) return <Screen><PageTop title="Payment Result" fallback="/(member)/renew" /><Busy label="Checking VNPay confirmation" /></Screen>;
  if (payment.isError) return <Screen><PageTop title="Payment Result" fallback="/(member)/renew" /><Message title="Status unavailable" detail={errorMessage(payment.error)} action="Try again" onAction={() => void payment.refetch()} tone="error" /></Screen>;

  const result = payment.data!;
  if (result.status === 'paid') return <Screen><PageTop title="Payment Result" fallback="/(member)/(tabs)/dashboard" /><Heading title={result.product_type === 'class_booking' ? 'Class booking confirmed' : 'Membership confirmed'} detail="VNPay's signed server notification has been processed." /><Message title="Payment successful" detail={`${formatMoney(result.amount_vnd)} · ${result.product_name}`} tone="success" /><Card><Text style={textStyles.muted}>Status: <Text style={textStyles.body}>{result.product_type === 'class_booking' ? result.booking_status ?? 'confirmed' : result.membership_status ?? 'active'}</Text></Text><Text style={textStyles.muted}>{result.product_type === 'class_booking' ? 'Session' : 'Coverage expiry'}: <Text style={textStyles.body}>{result.product_type === 'class_booking' && result.class_start_at ? formatDate(result.class_start_at) : result.membership_expiry_date ? formatDate(result.membership_expiry_date) : 'Updating'}</Text></Text>{result.discount_details ? <><Text style={textStyles.muted}>Applied discount: <Text style={textStyles.body}>{result.discount_details.pricing.applied_discount_percent}%</Text></Text><Text style={textStyles.muted}>Previous-month visits: <Text style={textStyles.body}>{result.discount_details.attended_days}/{result.discount_details.period_days}</Text></Text></> : null}</Card><Action label="View invoices" onPress={() => { void refreshMembershipQueryData(); router.replace('/(member)/invoices'); }} /><Action label={result.product_type === 'class_booking' ? 'My bookings' : 'Back to dashboard'} outline onPress={() => { void refreshMembershipQueryData(); router.replace(result.product_type === 'class_booking' ? '/(member)/bookings' : '/(member)/(tabs)/dashboard'); }} /></Screen>;
  if (result.status === 'paid_review') return <Screen><PageTop title="Payment Result" fallback="/(member)/(tabs)/classes" /><Message title="Payment received — staff review required" detail="The seat hold was no longer valid, so no extra seat was confirmed. Staff will resolve the refund." action="View bookings" onAction={() => router.replace('/(member)/bookings')} tone="error" /></Screen>;
  if (['failed', 'cancelled', 'expired'].includes(result.status)) return <Screen><PageTop title="Payment Result" fallback={result.product_type === 'class_booking' ? '/(member)/(tabs)/classes' : '/(member)/renew'} /><Message title={result.status === 'cancelled' ? 'Payment cancelled' : result.status === 'expired' ? 'Payment expired' : 'Payment unsuccessful'} detail={result.product_type === 'class_booking' ? 'No class seat was confirmed. A retry creates a new secure transaction.' : 'Your membership was not changed. A retry creates a new secure transaction.'} action="Try VNPay again" onAction={() => result.product_type === 'class_booking' ? router.replace('/(member)/(tabs)/classes') : router.replace({ pathname: '/(member)/renew/confirm', params: { planId: result.membership_plan_id ?? '' } })} tone="error" /></Screen>;

  return <Screen><PageTop title="Payment Result" fallback="/(member)/(tabs)/dashboard" /><Heading title={timedOut ? 'Confirmation is taking longer' : 'Waiting for confirmation'} detail="Only VNPay's signed server notification can confirm this purchase." /><Message title={timedOut ? 'Still processing' : 'Payment confirmation pending'} detail={timedOut ? 'Check again without repeating the payment.' : 'Keep this screen open for a moment.'} action="Check again" onAction={() => void payment.refetch()} /></Screen>;
}
