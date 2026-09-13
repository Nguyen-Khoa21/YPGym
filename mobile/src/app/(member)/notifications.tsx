import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Alert, Pressable, Text, View } from 'react-native';

import { Action, Busy, Card, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage, formatDate } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { queryClient } from '@/lib/query';
import type { NotificationPage } from '@/lib/types';

export default function NotificationsScreen() {
  const { request, user } = useAuth();
  const [page, setPage] = useState(1);
  const inbox = useQuery({ queryKey: ['notifications', user?.id, page], queryFn: ({ signal }) => request<NotificationPage>(`/notifications/me?page=${page}&page_size=20`, { signal }) });
  const mark = useMutation({ mutationFn: (id?: string) => request(id ? `/notifications/me/${id}/read` : '/notifications/me/read-all', { method: 'POST' }),
    onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['notifications'] }), queryClient.invalidateQueries({ queryKey: ['dashboard'] })]); },
    onError: (error) => Alert.alert('Could not update inbox', errorMessage(error)) });
  return <Screen refreshing={inbox.isRefetching} onRefresh={() => void inbox.refetch()}><PageTop title="Notifications" onBack={() => router.back()} /><Heading title="Your inbox" detail={inbox.data ? `${inbox.data.unread_count} unread` : undefined} />
    {inbox.data?.unread_count ? <Action label="Mark all read" onPress={() => mark.mutate(undefined)} disabled={mark.isPending} outline /> : null}
    {inbox.isLoading ? <Busy label="Loading notifications" /> : null}{inbox.isError ? <Message title="Inbox unavailable" detail={errorMessage(inbox.error)} action="Retry" onAction={() => void inbox.refetch()} /> : null}
    {inbox.data?.items.length === 0 ? <Message title="Your inbox is clear" detail="Membership and booking updates will appear here." /> : null}
    <View style={{ marginTop: 17 }}>{inbox.data?.items.map((item) => <Pressable accessibilityRole="button" key={item.id} onPress={() => { if (!item.read_at) mark.mutate(item.id); }}><Card accent={!item.read_at}><Text style={textStyles.subheading}>{item.title}</Text><Text style={textStyles.muted}>{item.message}</Text><Text style={textStyles.lime}>{formatDate(item.created_at)} · {item.read_at ? 'Read' : 'Unread'}</Text></Card></Pressable>)}</View>
    {inbox.data && page < inbox.data.page.pages ? <Action label="Next page" onPress={() => setPage(page + 1)} outline /> : null}{page > 1 ? <Action label="Previous page" onPress={() => setPage(page - 1)} outline /> : null}
  </Screen>;
}
