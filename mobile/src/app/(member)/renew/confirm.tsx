import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import * as Crypto from 'expo-crypto';
import { router, useLocalSearchParams } from 'expo-router';
import { Switch, Text, View } from 'react-native';

import { Action, Busy, Card, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatMoney } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { queryClient } from '@/lib/query';
import { colors } from '@/lib/theme';
import type { Plan, Purchase } from '@/lib/types';

export default function ConfirmRenewalScreen() {
  const { planId } = useLocalSearchParams<{ planId: string }>();
  const { request, user } = useAuth();
  const [confirmed, setConfirmed] = useState(false);
  const [idempotencyKey] = useState(() => Crypto.randomUUID());
  const plans = useQuery({ queryKey: ['plans'], queryFn: ({ signal }) => request<Plan[]>('/membership-plans', { signal }) });
  const plan = plans.data?.find((item) => item.id === planId && item.is_active);
  const purchase = useMutation({ mutationFn: () => request<Purchase>('/memberships/purchase', { method: 'POST', body: { plan_id: planId, idempotency_key: idempotencyKey, mock_payment_confirmed: confirmed } }),
    onSuccess: async (result) => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['dashboard'] }), queryClient.invalidateQueries({ queryKey: ['invoices'] })]); router.replace({ pathname: '/(member)/renew/success', params: { invoiceId: result.invoice.id } }); } });
  return <Screen><PageTop title="Review Membership" onBack={() => router.back()} /><Heading title="One last check" detail="YPGym uses a simulated payment for this project. No real payment method is charged." />
    {plans.isLoading ? <Busy label="Loading selected plan" /> : null}{plans.isError ? <Message title="Plan unavailable" detail={errorMessage(plans.error)} action="Retry" onAction={() => void plans.refetch()} /> : null}
    {plans.data && !plan ? <Message title="Plan unavailable" detail="Choose an active membership plan." action="View plans" onAction={() => router.replace('/(member)/renew')} /> : null}
    {plan ? <Card accent><Text style={textStyles.eyebrow}>Selected plan</Text><Text style={textStyles.subheading}>{plan.name}</Text><Text style={textStyles.muted}>{plan.duration_months} months</Text><Text style={{ color: colors.lime, fontSize: 32, fontWeight: '900' }}>{formatMoney(plan.final_price)}</Text><Text style={textStyles.muted}>The server calculates the final price and dates. You will receive an invoice after confirmation.</Text></Card> : null}
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginVertical: 18 }}><Switch accessibilityLabel="Confirm simulated payment" value={confirmed} onValueChange={setConfirmed} trackColor={{ true: colors.lime }} /><Text style={[textStyles.muted, { flex: 1 }]}>I confirm this simulated payment and membership purchase.</Text></View>
    {purchase.isError ? <Message title="Payment not completed" detail={errorMessage(purchase.error)} action="Retry" onAction={() => purchase.mutate()} /> : null}
    <Action label={purchase.isPending ? 'Confirming…' : 'Confirm mock payment'} disabled={!plan || !confirmed || purchase.isPending || !user?.is_email_verified} onPress={() => purchase.mutate()} />
    {!user?.is_email_verified ? <Text style={textStyles.muted}>Verify your email in the web app before purchasing.</Text> : null}
  </Screen>;
}
