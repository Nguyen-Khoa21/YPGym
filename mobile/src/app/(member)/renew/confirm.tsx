import { useMutation, useQuery } from '@tanstack/react-query';
import * as WebBrowser from 'expo-web-browser';
import { router, useLocalSearchParams, type Href } from 'expo-router';
import { Platform, Text } from 'react-native';

import { Action, Busy, Card, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatMoney } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { attendanceBenefitPath, gymChangeNotice, renewalCheckoutBody } from '@/lib/gyms';
import { colors } from '@/lib/theme';
import type { AttendanceBenefitQuote, Dashboard, GymLocation, PayOSCreateResponse, Plan } from '@/lib/types';

export default function ConfirmRenewalScreen() {
  const { planId, gymId } = useLocalSearchParams<{ planId: string; gymId?: string }>();
  const { request, user } = useAuth();
  const plans = useQuery({ queryKey: ['plans'], queryFn: ({ signal }) => request<Plan[]>('/membership-plans', { signal }) });
  const plan = plans.data?.find((item) => item.id === planId && item.is_active);
  const gyms = useQuery({ queryKey: ['gyms'], queryFn: ({ signal }) => request<GymLocation[]>('/gyms', { signal }) });
  const dashboard = useQuery({ queryKey: ['dashboard', user?.id], queryFn: ({ signal }) => request<Dashboard>('/dashboard/me', { signal }) });
  const gym = gymId ? gyms.data?.find((item) => item.id === gymId) : undefined;
  const home = dashboard.data?.membership;
  const benefit = useQuery({
    queryKey: ['attendance-benefit', planId, gymId ?? null],
    queryFn: ({ signal }) => request<AttendanceBenefitQuote>(attendanceBenefitPath(planId, gymId), { signal }),
    enabled: Boolean(plan),
  });
  const checkout = useMutation({
    mutationFn: () => request<PayOSCreateResponse>('/payments/payos/create', {
      method: 'POST',
      body: renewalCheckoutBody(planId, gymId, Platform.OS === 'web' ? 'mobile_web' : 'mobile'),
    }),
    onSuccess: async (result) => {
      router.push(`/payment-result?transaction_id=${encodeURIComponent(result.transaction_id)}&state=processing` as Href);
      if (Platform.OS === 'web') {
        window.location.assign(result.checkout_url);
      } else {
        await WebBrowser.openBrowserAsync(result.checkout_url);
      }
    },
  });

  return <Screen><PageTop title="payOS VietQR" fallback="/(member)/renew" /><Heading title="Confirm your membership" detail="payOS handles the VietQR transfer. YPGym activates coverage only after a signed webhook." />
    {plans.isLoading ? <Busy label="Loading selected plan" /> : null}{plans.isError ? <Message title="Plan unavailable" detail={errorMessage(plans.error)} action="Retry" onAction={() => void plans.refetch()} tone="error" /> : null}
    {plans.data && !plan ? <Message title="Plan unavailable" detail="Choose an active membership plan." action="View plans" onAction={() => router.replace('/(member)/renew')} /> : null}
    {plan ? <Card accent><Text style={textStyles.eyebrow}>Selected plan</Text><Text style={textStyles.subheading}>{plan.name}</Text><Text style={textStyles.muted}>{plan.duration_months} months</Text><Text style={{ color: colors.primary, fontSize: 32, fontWeight: '900' }}>{formatMoney(benefit.data?.pricing.final_amount ?? plan.final_price)}</Text><Text style={textStyles.muted}>The server calculates the final price. payOS provides a Napas 24/7 VietQR transfer.</Text></Card> : null}
    {gymId ? <Card><Text style={textStyles.eyebrow}>Gym</Text><Text style={textStyles.subheading}>{gym?.name ?? 'Selected gym'}</Text>{gym ? <Text style={textStyles.muted}>{gym.address}</Text> : null}<Text style={textStyles.muted}>{gymChangeNotice(gym?.name ?? null, gymId, home?.home_gym_name, home?.home_gym_id)}</Text></Card> : null}
    {benefit.isLoading ? <Busy label="Checking attendance benefit" /> : null}
    {benefit.isError ? <Message title="Price unavailable" detail={errorMessage(benefit.error)} action="Retry" onAction={() => void benefit.refetch()} tone="error" /> : null}
    {benefit.data ? <Card><Text style={textStyles.eyebrow}>Previous-month attendance</Text><Text style={textStyles.subheading}>{benefit.data.attended_days}/{benefit.data.period_days} days · {benefit.data.attendance_percentage}%</Text><Text style={textStyles.body}>{benefitMessage(benefit.data)}</Text><Text style={textStyles.muted}>Plan discount: {benefit.data.pricing.plan_discount_percent}% · Attendance discount: {benefit.data.pricing.attendance_discount_percent}% · Applied: {benefit.data.pricing.applied_discount_percent}%</Text><Text style={textStyles.muted}>{benefit.data.period_start} to {benefit.data.period_end}. The higher discount applies, and attendance eligibility is consumed after one successful renewal.</Text></Card> : null}
    <Card><Text style={textStyles.subheading}>payOS VietQR</Text><Text style={textStyles.muted}>You will leave YPGym briefly to complete checkout. Returning does not activate the membership until the signed webhook is verified.</Text></Card>
    {checkout.isError ? <Message title="Checkout not started" detail={errorMessage(checkout.error)} action="Retry" onAction={() => checkout.mutate()} tone="error" /> : null}
    <Action label={checkout.isPending ? 'Preparing VietQR…' : 'Continue to payOS'} disabled={!plan || !benefit.data || benefit.data.status === 'pending' || checkout.isPending || !user?.is_email_verified} onPress={() => checkout.mutate()} />
    {!user?.is_email_verified ? <Text style={textStyles.muted}>Verify your email before purchasing.</Text> : null}
  </Screen>;
}

function benefitMessage(value: AttendanceBenefitQuote) {
  if (value.status === 'eligible') return value.pricing.attendance_benefit_selected ? 'Attendance benefit selected under the better-of rule.' : 'Your plan discount is higher, so it applies under the better-of rule.';
  if (value.status === 'pending') return 'An attendance-discounted renewal is already pending.';
  if (value.status === 'consumed') return 'This attendance month has already been used for a successful renewal.';
  if (value.status === 'not_renewal') return 'Attendance benefits apply to active membership renewals, not first purchases.';
  return `Reach ${Number(value.threshold_percentage)}% of the previous calendar month to qualify.`;
}
