import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Alert, Text, View } from 'react-native';

import { Action, Busy, Card, Field, Heading, Message, PageTop, Pill, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { queryClient } from '@/lib/query';
import type { MembershipRequest } from '@/lib/types';

type FormErrors = { start?: string; end?: string; freezeReason?: string; cancellationReason?: string };

export default function MembershipRequestsScreen() {
  const { request, user } = useAuth();
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [freezeReason, setFreezeReason] = useState('');
  const [cancellationReason, setCancellationReason] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const history = useQuery({ queryKey: ['membership-requests', user?.id], queryFn: ({ signal }) => request<MembershipRequest[]>('/memberships/requests/me', { signal }) });
  const create = useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) => request<MembershipRequest>(path, { method: 'POST', body }),
    onSuccess: async () => { setStart(''); setEnd(''); setFreezeReason(''); setCancellationReason(''); setErrors({}); await queryClient.invalidateQueries({ queryKey: ['membership-requests'] }); Alert.alert('Request submitted', 'Gym staff can now review it.'); },
    onError: (error) => Alert.alert('Could not submit request', errorMessage(error)),
  });

  function submitFreeze() {
    const startDate = /^\d{4}-\d{2}-\d{2}$/.test(start) ? new Date(`${start}T00:00:00Z`) : null;
    const endDate = /^\d{4}-\d{2}-\d{2}$/.test(end) ? new Date(`${end}T00:00:00Z`) : null;
    const days = startDate && endDate ? Math.round((endDate.getTime() - startDate.getTime()) / 86400000) + 1 : 0;
    const next: FormErrors = { ...(!startDate ? { start: 'Use YYYY-MM-DD.' } : {}), ...(!endDate ? { end: 'Use YYYY-MM-DD.' } : {}), ...(startDate && endDate && days < 1 ? { end: 'End date must be on or after start date.' } : {}), ...(days > 90 ? { end: 'Freeze requests cannot exceed 90 days.' } : {}), ...(freezeReason.trim().length < 10 ? { freezeReason: 'Enter at least 10 characters.' } : {}) };
    setErrors(next);
    if (Object.keys(next).length) return;
    create.mutate({ path: '/memberships/freeze-requests', body: { requested_start_date: start, requested_end_date: end, reason: freezeReason.trim() } });
  }

  function submitCancellation() {
    const next = cancellationReason.trim().length < 10 ? { cancellationReason: 'Enter at least 10 characters.' } : {};
    setErrors(next);
    if (Object.keys(next).length) return;
    create.mutate({ path: '/memberships/cancellation-requests', body: { reason: cancellationReason.trim() } });
  }

  return <Screen refreshing={history.isRefetching} onRefresh={() => void history.refetch()}><PageTop title="Membership Requests" fallback="/(member)/(tabs)/profile" /><Heading title="Pause or close your membership" detail="Requests are reviewed by gym staff and remain visible in your history." />
    <Card accent><Text style={textStyles.subheading}>Request a freeze</Text><Text style={textStyles.muted}>Enter dates as YYYY-MM-DD. A freeze can cover up to 90 days.</Text><View style={{ gap: 12 }}><Field label="Start date" value={start} onChangeText={setStart} placeholder="2026-10-01" error={errors.start} autoCapitalize="none" /><Field label="End date" value={end} onChangeText={setEnd} placeholder="2026-10-14" error={errors.end} autoCapitalize="none" /><Field label="Reason" value={freezeReason} onChangeText={setFreezeReason} multiline numberOfLines={4} textAlignVertical="top" style={{ minHeight: 104, paddingTop: 14 }} error={errors.freezeReason} /><Action label={create.isPending ? 'Submitting…' : 'Submit freeze request'} disabled={create.isPending} onPress={submitFreeze} /></View></Card>
    <Card><Text style={textStyles.subheading}>Request cancellation</Text><Text style={textStyles.muted}>Staff will record the decision and any refund, account credit or forfeit outcome.</Text><Field label="Cancellation reason" value={cancellationReason} onChangeText={setCancellationReason} multiline numberOfLines={4} textAlignVertical="top" style={{ minHeight: 104, paddingTop: 14 }} error={errors.cancellationReason} /><Action label={create.isPending ? 'Submitting…' : 'Submit cancellation request'} disabled={create.isPending} danger onPress={submitCancellation} /></Card>
    <Heading title="Request history" detail="Open duplicate requests are blocked by the server." />
    {history.isLoading ? <Busy label="Loading membership requests" /> : null}{history.isError ? <Message title="History unavailable" detail={errorMessage(history.error)} action="Retry" onAction={() => void history.refetch()} tone="error" /> : null}
    {history.data?.length === 0 ? <Message title="No membership requests" detail="Submitted freeze and cancellation requests will appear here." /> : null}
    {history.data?.map((item) => <Card key={item.id}><Pill label={item.status} tone={item.status === 'approved' ? 'positive' : item.status === 'rejected' ? 'danger' : 'warning'} /><Text style={textStyles.subheading}>{item.request_type === 'freeze' ? 'Freeze request' : 'Cancellation request'}</Text><Text style={textStyles.body}>{item.reason}</Text>{item.requested_start_date ? <Text style={textStyles.muted}>{formatDate(item.requested_start_date)} to {formatDate(item.requested_end_date!)}</Text> : null}<Text style={textStyles.muted}>Submitted {formatDate(item.created_at)}</Text>{item.decision_reason ? <Text style={textStyles.accent}>{item.decision_reason}{item.outcome ? ` · ${item.outcome.replaceAll('_', ' ')}` : ''}</Text> : null}</Card>)}
  </Screen>;
}
