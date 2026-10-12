import { useMutation, useQuery } from '@tanstack/react-query';
import * as WebBrowser from 'expo-web-browser';
import { router, useLocalSearchParams, type Href } from 'expo-router';
import { Platform, Text } from 'react-native';

import { Action, Busy, Card, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatMoney } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';
import type { AttendanceBenefitQuote, Plan, VNPayCreateResponse } from '@/lib/types';

export default function ConfirmRenewalScreen() {
  const { planId } = useLocalSearchParams<{ planId: string }>();
  const { request, user } = useAuth();
  const plans = useQuery({ queryKey: ['plans'], queryFn: ({ signal }) => request<Plan[]>('/membership-plans', { signal }) });
  const plan = plans.data?.find((item) => item.id === planId && item.is_active);
  const benefit = useQuery({
    queryKey: ['attendance-benefit', planId],
    queryFn: ({ signal }) => request<AttendanceBenefitQuote>(`/memberships/attendance-benefit/me?plan_id=${planId}`, { signal }),
    enabled: Boolean(plan),
  });
  const checkout = useMutation({
    mutationFn: () => request<VNPayCreateResponse>('/payments/vnpay/create', {
      method: 'POST',
      body: { membership_plan_id: planId, locale: 'vn', bank_code: null, client_platform: Platform.OS === 'web' ? 'mobile_web' : 'mobile' },
    }),
    onSuccess: async (result) => {
      router.push(`/payment-result?transaction_id=${encodeURIComponent(result.transaction_id)}&state=processing` as Href);
      if (Platform.OS === 'web') {
        window.location.assign(result.payment_url);
      } else {
        await WebBrowser.openBrowserAsync(result.payment_url);
      }
    },
  });

  return <Screen><PageTop title="VNPay Checkout" fallback="/(member)/renew" /><Heading title="Confirm your membership" detail="VNPay handles the payment. YPGym activates coverage only after a signed server confirmation." />
    {plans.isLoading ? <Busy label="Loading selected plan" /> : null}{plans.isError ? <Message title="Plan unavailable" detail={errorMessage(plans.error)} action="Retry" onAction={() => void plans.refetch()} tone="error" /> : null}
    {plans.data && !plan ? <Message title="Plan unavailable" detail="Choose an active membership plan." action="View plans" onAction={() => router.replace('/(member)/renew')} /> : null}
    {plan ? <Card accent><Text style={textStyles.eyebrow}>Selected plan</Text><Text style={textStyles.subheading}>{plan.name}</Text><Text style={textStyles.muted}>{plan.duration_months} months</Text><Text style={{ color: colors.primary, fontSize: 32, fontWeight: '900' }}>{formatMoney(benefit.data?.pricing.final_amount ?? plan.final_price)}</Text><Text style={textStyles.muted}>The server calculates the final price. VNPay lets you choose a supported bank, card or QR method.</Text></Card> : null}
    {benefit.isLoading ? <Busy label="Checking attendance benefit" /> : null}
    {benefit.isError ? <Message title="Price unavailable" detail={errorMessage(benefit.error)} action="Retry" onAction={() => void benefit.refetch()} tone="error" /> : null}
    {benefit.data ? <Card><Text style={textStyles.eyebrow}>Previous-month attendance</Text><Text style={textStyles.subheading}>{benefit.data.attended_days}/{benefit.data.period_days} days · {benefit.data.attendance_percentage}%</Text><Text style={textStyles.body}>{benefitMessage(benefit.data)}</Text><Text style={textStyles.muted}>Plan discount: {benefit.data.pricing.plan_discount_percent}% · Attendance discount: {benefit.data.pricing.attendance_discount_percent}% · Applied: {benefit.data.pricing.applied_discount_percent}%</Text><Text style={textStyles.muted}>{benefit.data.period_start} to {benefit.data.period_end}. The higher discount applies, and attendance eligibility is consumed after one successful renewal.</Text></Card> : null}
    <Card><Text style={textStyles.subheading}>VNPay</Text><Text style={textStyles.muted}>You will leave YPGym briefly to complete the sandbox checkout. Returning to the app does not activate the membership until the server notification is verified.</Text></Card>
    {checkout.isError ? <Message title="Checkout not started" detail={errorMessage(checkout.error)} action="Retry" onAction={() => checkout.mutate()} tone="error" /> : null}
    <Action label={checkout.isPending ? 'Preparing VNPay…' : 'Continue to VNPay'} disabled={!plan || !benefit.data || benefit.data.status === 'pending' || checkout.isPending || !user?.is_email_verified} onPress={() => checkout.mutate()} />
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
