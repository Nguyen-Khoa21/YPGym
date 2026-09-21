import { useQuery } from '@tanstack/react-query';
import { Text } from 'react-native';

import { Busy, Card, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate, formatMoney } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { Invoice } from '@/lib/types';

export default function InvoicesScreen() {
  const { request, user } = useAuth();
  const invoices = useQuery({ queryKey: ['invoices', user?.id], queryFn: ({ signal }) => request<Invoice[]>('/billing/me/invoices', { signal }) });
  return <Screen refreshing={invoices.isRefetching} onRefresh={() => void invoices.refetch()}><PageTop title="Invoices" fallback="/(member)/(tabs)/profile" /><Heading title="Payment records" detail="Confirmed simulated payments and immutable invoice details." />
    {invoices.isLoading ? <Busy label="Loading invoices" /> : null}{invoices.isError ? <Message title="Invoices unavailable" detail={errorMessage(invoices.error)} action="Retry" onAction={() => void invoices.refetch()} /> : null}
    {invoices.data?.length === 0 ? <Message title="No invoices yet" detail="A successful membership purchase will appear here." /> : null}
    {invoices.data?.map((item) => <Card key={item.id}><Text style={textStyles.subheading}>{item.plan_name}</Text><Text style={textStyles.lime}>{formatMoney(item.amount)}</Text><Text style={textStyles.muted}>Invoice {item.invoice_number} · {formatDate(item.transaction_date)}</Text><Text style={textStyles.muted}>Coverage expires {formatDate(item.membership_expiry_date)}</Text></Card>)}
  </Screen>;
}
