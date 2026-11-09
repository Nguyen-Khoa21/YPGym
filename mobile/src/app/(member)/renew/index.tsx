import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import { Action, Busy, Card, Heading, Message, PageTop, Pill, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatMoney } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { isChangeLocation } from '@/lib/expired';
import { activeGyms, renewalGymId } from '@/lib/gyms';
import { colors } from '@/lib/theme';
import type { Recommendations } from '@/lib/onboarding';
import type { Dashboard, GymLocation, Plan } from '@/lib/types';

export default function RenewScreen() {
  const { request, user } = useAuth();
  const changeLocation = isChangeLocation(useLocalSearchParams<{ mode?: string | string[] }>().mode);
  const [selected, setSelected] = useState<string | null>(null);
  const [pickedGym, setPickedGym] = useState<string | null>(null);
  const dashboard = useQuery({ queryKey: ['dashboard', user?.id], queryFn: ({ signal }) => request<Dashboard>('/dashboard/me', { signal }), staleTime: 0, refetchOnMount: 'always' });
  const plans = useQuery({ queryKey: ['plans'], queryFn: ({ signal }) => request<Plan[]>('/membership-plans', { signal }) });
  const gyms = useQuery({ queryKey: ['gyms'], queryFn: ({ signal }) => request<GymLocation[]>('/gyms', { signal }) });
  const recommendations = useQuery({ queryKey: ['recommendations', user?.id], staleTime: 300_000, queryFn: ({ signal }) => request<Recommendations>('/users/me/recommendations', { signal }) });
  const recommendedGymId = recommendations.data?.recommended_gym?.id ?? null;
  const activePlans = plans.data?.filter((plan) => plan.is_active) ?? [];
  const homeGymId = dashboard.data?.membership?.home_gym_id;
  // A recommendation only preselects a gym for members who have no home gym yet.
  const gymId = renewalGymId(gyms.data, pickedGym ?? (dashboard.isSuccess && !homeGymId ? recommendedGymId : null), changeLocation ? null : homeGymId);
  const gymChoices = activeGyms(gyms.data);
  return <Screen><PageTop title="Renew Membership" fallback="/(member)/(tabs)/dashboard" /><Heading title="Current Status" />
    {dashboard.isLoading ? <Busy label="Loading membership" /> : null}{dashboard.isError ? <Message title="Membership unavailable" detail={errorMessage(dashboard.error)} action="Retry" onAction={() => void dashboard.refetch()} tone="error" /> : null}
    {dashboard.data ? <Card accent><Text style={textStyles.eyebrow}>{dashboard.data.membership ? `${dashboard.data.membership.status} plan` : 'No current plan'}</Text><Text style={textStyles.subheading}>{dashboard.data.membership?.plan_name ?? 'Choose your membership'}</Text>{dashboard.data.membership ? <><View style={{ flexDirection: 'row', alignItems: 'baseline', flexWrap: 'wrap', gap: 8 }}><Text style={{ color: colors.primary, fontSize: 39, lineHeight: 48, fontWeight: '900' }}>{dashboard.data.membership.days_remaining}</Text><Text style={textStyles.muted}>days remaining</Text></View><Pill label={dashboard.data.membership.status} tone={dashboard.data.qr_access.eligible ? 'positive' : 'danger'} /><Text style={textStyles.muted}>{dashboard.data.membership.message}</Text></> : <Text style={textStyles.muted}>Your plan will begin when the server confirms this registration.</Text>}</Card> : null}
    <Text style={[textStyles.subheading, { marginTop: 18, marginBottom: 6 }]}>Choose your gym</Text>
    <Text style={[textStyles.muted, { marginBottom: 12 }]}>{homeGymId ? 'Your current gym is selected. Pick another gym to move. Your home gym changes only after payment succeeds.' : 'Pick the gym you want to join. You can only use the gym you pay for.'}</Text>
    {gyms.isLoading ? <Busy label="Loading gyms" /> : null}{gyms.isError ? <Message title="Gyms unavailable" detail={errorMessage(gyms.error)} action="Retry" onAction={() => void gyms.refetch()} tone="error" /> : null}
    {gyms.data && !gymChoices.length ? <Message title="No active gyms" detail="Please contact YPGym before renewing." /> : null}
    {gymChoices.map((gym) => <Pressable accessibilityRole="radio" accessibilityState={{ selected: gymId === gym.id }} key={gym.id} onPress={() => setPickedGym(gym.id)}><Card accent={gymId === gym.id}><View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}><Text style={[textStyles.subheading, { flex: 1 }]}>{gym.name}</Text>{homeGymId === gym.id ? <Pill label="Your gym" /> : recommendedGymId === gym.id ? <Pill label="Recommended for you" /> : null}</View><Text style={textStyles.muted}>{gym.address}</Text></Card></Pressable>)}
    <Text style={[textStyles.subheading, { marginTop: 18, marginBottom: 15 }]}>Select a New Plan</Text>
    {plans.isLoading ? <Busy label="Loading plans" /> : null}{plans.isError ? <Message title="Plans unavailable" detail={errorMessage(plans.error)} action="Retry" onAction={() => void plans.refetch()} tone="error" /> : null}
    {plans.data && !activePlans.length ? <Message title="No active plans" detail="Please contact the gym before renewing." /> : null}
    {activePlans.map((plan) => <Pressable accessibilityRole="radio" accessibilityState={{ selected: selected === plan.id }} key={plan.id} onPress={() => setSelected(plan.id)}><Card accent={selected === plan.id}><View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}><Text style={[textStyles.subheading, { flex: 1 }]}>{plan.name}</Text><Text style={textStyles.accent}>{formatMoney(plan.final_price)}</Text></View><Text style={textStyles.muted}>{plan.duration_months} months · {plan.discount_percent}% discount</Text>{plan.benefits.map((benefit) => <Text key={benefit} style={textStyles.muted}>✓ {benefit}</Text>)}</Card></Pressable>)}
    <Action label="Review membership registration →" disabled={!selected || !gymId} onPress={() => { if (selected && gymId) router.push({ pathname: '/(member)/renew/confirm', params: { planId: selected, gymId } }); }} />
    {selected && !gymId && gyms.data ? <Text style={textStyles.muted}>Choose a gym to continue.</Text> : null}
  </Screen>;
}
