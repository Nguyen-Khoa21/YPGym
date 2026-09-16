import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import { Action, Busy, Card, Heading, Message, PageTop, Pill, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatMoney } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';
import type { Dashboard, Plan } from '@/lib/types';

export default function RenewScreen() {
  const { request, user } = useAuth();
  const [selected, setSelected] = useState<string | null>(null);
  const dashboard = useQuery({ queryKey: ['dashboard', user?.id], queryFn: ({ signal }) => request<Dashboard>('/dashboard/me', { signal }) });
  const plans = useQuery({ queryKey: ['plans'], queryFn: ({ signal }) => request<Plan[]>('/membership-plans', { signal }) });
  const activePlans = plans.data?.filter((plan) => plan.is_active) ?? [];
  return <Screen><PageTop title="Renew Membership" onBack={() => router.back()} /><Heading title="Current Status" />
    {dashboard.isLoading ? <Busy label="Loading membership" /> : null}{dashboard.isError ? <Message title="Membership unavailable" detail={errorMessage(dashboard.error)} action="Retry" onAction={() => void dashboard.refetch()} /> : null}
    {dashboard.data ? <Card accent><Text style={textStyles.eyebrow}>{dashboard.data.membership ? 'Active plan' : 'No current plan'}</Text><Text style={textStyles.subheading}>{dashboard.data.membership?.plan_name ?? 'Choose your membership'}</Text>{dashboard.data.membership ? <><View style={{ flexDirection: 'row', alignItems: 'baseline', flexWrap: 'wrap', gap: 8 }}><Text style={{ color: colors.lime, fontSize: 39, lineHeight: 48, fontWeight: '900' }}>{dashboard.data.membership.days_remaining}</Text><Text style={textStyles.muted}>days remaining</Text></View><Pill label={dashboard.data.membership.status} /></> : <Text style={textStyles.muted}>Your plan will begin when the backend confirms the simulated payment.</Text>}</Card> : null}
    <Text style={[textStyles.subheading, { marginTop: 18, marginBottom: 15 }]}>Select a New Plan</Text>
    {plans.isLoading ? <Busy label="Loading plans" /> : null}{plans.isError ? <Message title="Plans unavailable" detail={errorMessage(plans.error)} action="Retry" onAction={() => void plans.refetch()} /> : null}
    {plans.data && !activePlans.length ? <Message title="No active plans" detail="Please contact the gym before renewing." /> : null}
    {activePlans.map((plan) => <Pressable accessibilityRole="radio" accessibilityState={{ selected: selected === plan.id }} key={plan.id} onPress={() => setSelected(plan.id)}><Card accent={selected === plan.id}><View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}><Text style={[textStyles.subheading, { flex: 1 }]}>{plan.name}</Text><Text style={textStyles.lime}>{formatMoney(plan.final_price)}</Text></View><Text style={textStyles.muted}>{plan.duration_months} months · {plan.discount_percent}% discount</Text>{plan.benefits.map((benefit) => <Text key={benefit} style={textStyles.muted}>✓ {benefit}</Text>)}</Card></Pressable>)}
    <Action label="Proceed to mock payment →" disabled={!selected} onPress={() => { if (selected) router.push({ pathname: '/(member)/renew/confirm', params: { planId: selected } }); }} />
  </Screen>;
}
