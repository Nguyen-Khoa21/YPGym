import { useQuery } from '@tanstack/react-query';
import { Text } from 'react-native';

import { Busy, Card, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatMoney } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { Invoice } from '@/lib/types';

export default function InvoicesScreen() {
  const { request, user } = useAuth();
  const invoices = useQuery({ queryKey: ['invoices', user?.id], queryFn: ({ signal }) => request<Invoice[]>('/billing/me/invoices', { signal }) });
  return <Screen refreshing={invoices.isRefetching} onRefresh={() => void invoices.refetch()}><PageTop title="Invoices" fallback="/(member)/(tabs)/profile" /><Heading title="Payment records" detail="Confirmed payments and immutable invoice details." />
    {invoices.isLoading ? <Busy label="Loading invoices" /> : null}{invoices.isError ? <Message title="Invoices unavailable" detail={errorMessage(invoices.error)} action="Retry" onAction={() => void invoices.refetch()} tone="error" /> : null}
    {invoices.data?.length === 0 ? <Message title="No invoices yet" detail="A successful membership or class purchase will appear here." /> : null}
    {invoices.data?.map((item) => <Card key={item.id}><Text style={textStyles.subheading}>{item.product_name}</Text><Text style={textStyles.accent}>{formatMoney(item.amount)}</Text><Text style={textStyles.muted}>{item.product_type === 'class_booking' ? 'Class booking' : 'Membership'} · Invoice {item.invoice_number}</Text><Text style={textStyles.muted}>{item.product_type === 'class_booking' && item.service_start_at ? `Session ${formatDate(item.service_start_at)}` : item.membership_expiry_date ? `Coverage expires ${formatDate(item.membership_expiry_date)}` : formatDate(item.transaction_date)}</Text>{item.discount_details ? <Text style={textStyles.muted}>Better-of discount {item.discount_details.pricing.applied_discount_percent}% · Attendance {item.discount_details.attended_days}/{item.discount_details.period_days} days</Text> : null}</Card>)}
  </Screen>;
}
