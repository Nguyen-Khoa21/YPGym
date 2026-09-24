import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { Text, View } from 'react-native';

import { Action, Busy, Card, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatMoney } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';
import type { Invoice } from '@/lib/types';

export default function RenewalSuccessScreen() {
  const { invoiceId } = useLocalSearchParams<{ invoiceId: string }>();
  const { request, user } = useAuth();
  const invoices = useQuery({ queryKey: ['invoices', user?.id], queryFn: ({ signal }) => request<Invoice[]>('/billing/me/invoices', { signal }), enabled: Boolean(invoiceId) });
  const invoice = invoices.data?.find((item) => item.id === invoiceId);
  return <Screen><PageTop title="Renewal Complete" fallback="/(member)/(tabs)/dashboard" /><View style={{ flex: 1, justifyContent: 'center', minHeight: 520, gap: 18 }}>
    {invoices.isLoading ? <Busy label="Verifying your invoice" /> : null}
    {invoices.isError ? <Message title="Could not verify renewal" detail={errorMessage(invoices.error)} action="Retry" onAction={() => void invoices.refetch()} tone="error" /> : null}
    {invoices.data && !invoice ? <Message title="Renewal receipt unavailable" detail="This screen only confirms an invoice returned by your account." action="View invoices" onAction={() => router.replace('/(member)/invoices')} tone="error" /> : null}
    {invoice ? <><View style={{ alignItems: 'center', gap: 14 }}><View style={{ width: 92, height: 92, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.positiveSurface, borderColor: colors.positiveBorder, borderWidth: 1, borderRadius: 30 }}><Text style={{ color: colors.primary, fontSize: 54, fontWeight: '900' }}>✓</Text></View><Text style={[textStyles.heading, { textAlign: 'center' }]}>Membership Renewed!</Text><Text style={[textStyles.muted, { textAlign: 'center' }]}>Your simulated payment succeeded and your membership coverage has been updated.</Text></View>
      <Card><Text style={textStyles.muted}>Plan: <Text style={textStyles.body}>{invoice.plan_name}</Text></Text><Text style={textStyles.muted}>New expiry: <Text style={textStyles.body}>{formatDate(invoice.membership_expiry_date)}</Text></Text><Text style={textStyles.muted}>Registered amount: <Text style={textStyles.accent}>{formatMoney(invoice.amount)}</Text></Text><Text style={textStyles.muted}>Invoice: {invoice.invoice_number}</Text></Card>
      <Action label="View invoice" outline onPress={() => router.push('/(member)/invoices')} /><Action label="Back to dashboard" onPress={() => router.replace('/(member)/(tabs)/dashboard')} />
    </> : null}
  </View></Screen>;
}
