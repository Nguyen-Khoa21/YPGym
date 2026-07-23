import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { MetricCard, OperationsHeader, Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { NotificationPage } from "@/types/operations";

export function NotificationsPage() {
  const { token } = useAuth();
  const [page, setPage] = useState(1);
  const notifications = useQuery({ queryKey: ["notifications", "inbox", page], queryFn: ({ signal }) => apiRequest<NotificationPage>(`/notifications/me?page=${page}&page_size=20`, { token, signal }) });
  const readAll = useMutation({ mutationFn: () => apiRequest("/notifications/me/read-all", { method: "POST", token }), onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["notifications"] }), queryClient.invalidateQueries({ queryKey: ["dashboard"] })]); } });
  const readOne = useMutation({ mutationFn: (id: string) => apiRequest(`/notifications/me/${id}/read`, { method: "POST", token }), onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["notifications"] }), queryClient.invalidateQueries({ queryKey: ["dashboard"] })]); } });
  return <MemberShell><div className="mx-auto max-w-5xl"><OperationsHeader kicker="Notification inbox" title="Nothing important gets lost." description="Real in-app records from membership reminders and supported communication workflows." actions={<Button variant="outline" disabled={!notifications.data?.unread_count || readAll.isPending} onClick={() => readAll.mutate()}><CheckCheck className="size-4" /> Mark all read</Button>} />
    {notifications.data ? <div className="ops-metrics"><MetricCard label="Unread" value={notifications.data.unread_count} tone="lime" /><MetricCard label="All notifications" value={notifications.data.page.total} tone="forest" /><MetricCard label="Delivery" value="In app" /><MetricCard label="Preference aware" value="Yes" tone="coral" /></div> : null}
    {notifications.isLoading ? <LoadingState className="mt-6" title="Loading notifications" /> : null}{notifications.isError ? <ErrorState className="mt-6" title={toUiError(notifications.error).title} message={toUiError(notifications.error).message} /> : null}
    {notifications.data?.items.length === 0 ? <EmptyState className="mt-6" title="Your inbox is clear" message="Expiry reminders and other supported notices will appear here." /> : null}
    {notifications.data?.items.length ? <Panel title="Recent notifications"><div className="grid gap-2 p-4">{notifications.data.items.map((item) => <button className={`flex w-full items-start gap-4 rounded-xl border p-4 text-left transition-colors ${item.read_at ? "border-border bg-card" : "border-secondary bg-secondary/10"}`} key={item.id} onClick={() => { if (!item.read_at) readOne.mutate(item.id); }}><span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary text-secondary"><Bell className="size-5" /></span><span className="min-w-0 flex-1"><span className="flex flex-wrap items-center justify-between gap-2"><strong className="text-sm">{item.title}</strong><StatusBadge value={item.read_at ? "read" : "unread"} /></span><span className="mt-1 block text-xs leading-5 text-muted-foreground">{item.message}</span><small className="mt-2 block text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{formatDateTime(item.created_at)} / {item.category}</small></span></button>)}</div><Pagination page={page} pages={notifications.data.page.pages} total={notifications.data.page.total} onPage={setPage} /></Panel> : null}
  </div></MemberShell>;
}
