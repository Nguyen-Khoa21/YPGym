import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import * as Crypto from 'expo-crypto';
import { router, useLocalSearchParams } from 'expo-router';
import { Text } from 'react-native';

import { Action, Busy, Card, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatMoney } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { refreshMembershipQueryData } from '@/lib/query';
import { colors } from '@/lib/theme';
import type { Plan, Purchase } from '@/lib/types';

export default function ConfirmRenewalScreen() {
  const { planId } = useLocalSearchParams<{ planId: string }>();
  const { request, user } = useAuth();
  const [idempotencyKey] = useState(() => Crypto.randomUUID());
  const plans = useQuery({ queryKey: ['plans'], queryFn: ({ signal }) => request<Plan[]>('/membership-plans', { signal }) });
  const plan = plans.data?.find((item) => item.id === planId && item.is_active);
  const purchase = useMutation({ mutationFn: () => request<Purchase>('/memberships/purchase', { method: 'POST', body: { plan_id: planId, idempotency_key: idempotencyKey, mock_payment_confirmed: true } }),
    onSuccess: async (result) => { await refreshMembershipQueryData(); router.replace({ pathname: '/(member)/renew/success', params: { invoiceId: result.invoice.id } }); } });
  return <Screen><PageTop title="Register Membership" fallback="/(member)/renew" /><Heading title="Confirm your membership" detail="The YPGym server will activate your coverage and create an invoice for this registration." />
    {plans.isLoading ? <Busy label="Loading selected plan" /> : null}{plans.isError ? <Message title="Plan unavailable" detail={errorMessage(plans.error)} action="Retry" onAction={() => void plans.refetch()} tone="error" /> : null}
    {plans.data && !plan ? <Message title="Plan unavailable" detail="Choose an active membership plan." action="View plans" onAction={() => router.replace('/(member)/renew')} /> : null}
    {plan ? <Card accent><Text style={textStyles.eyebrow}>Selected plan</Text><Text style={textStyles.subheading}>{plan.name}</Text><Text style={textStyles.muted}>{plan.duration_months} months</Text><Text style={{ color: colors.primary, fontSize: 32, fontWeight: '900' }}>{formatMoney(plan.final_price)}</Text><Text style={textStyles.muted}>The server calculates the final price and dates. You will receive an invoice after confirmation.</Text></Card> : null}
    {purchase.isError ? <Message title="Registration not completed" detail={errorMessage(purchase.error)} action="Retry" onAction={() => purchase.mutate()} tone="error" /> : null}
    <Action label={purchase.isPending ? 'Registering…' : 'Complete membership registration'} disabled={!plan || purchase.isPending || !user?.is_email_verified} onPress={() => purchase.mutate()} />
    {!user?.is_email_verified ? <Text style={textStyles.muted}>Verify your email in the web app before purchasing.</Text> : null}
  </Screen>;
}
