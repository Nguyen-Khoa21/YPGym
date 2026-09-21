import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Gauge, QrCode, RefreshCw, Settings2, TimerReset, UsersRound } from "lucide-react";
import { toast } from "sonner";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { OperationsHeader, Panel } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { queryClient } from "@/lib/queryClient";
import type { ConfigurationItem } from "@/types/operations";

const labels: Record<string, { title: string; unit: string; icon: typeof Gauge }> = {
  gym_capacity: { title: "Gym capacity", unit: "people", icon: UsersRound },
  qr_token_ttl_seconds: { title: "QR token lifetime", unit: "seconds", icon: QrCode },
  attendance_timeout_minutes: { title: "Attendance timeout", unit: "minutes", icon: TimerReset },
  duplicate_scan_window_seconds: { title: "Duplicate scan window", unit: "seconds", icon: RefreshCw },
  class_cancellation_window_hours: { title: "Class cancellation window", unit: "hours", icon: Settings2 },
  class_reminder_lead_minutes: { title: "Class reminder lead time", unit: "minutes", icon: TimerReset },
  waitlist_size: { title: "Default waitlist limit", unit: "members", icon: Gauge },
};

export function AdminSettingsPage() {
  const { token } = useAuth();
  const settings = useQuery({ queryKey: ["admin", "configuration"], queryFn: ({ signal }) => apiRequest<ConfigurationItem[]>("/admin/configuration", { token, signal }) });
  const [values, setValues] = useState<Record<string, number>>({});
  const update = useMutation({ mutationFn: ({ key, value }: { key: string; value: number }) => apiRequest<ConfigurationItem>(`/admin/configuration/${key}`, { method: "PATCH", token, body: { value } }), onSuccess: async (item) => { setValues((current) => { const next = { ...current }; delete next[item.key]; return next; }); await queryClient.invalidateQueries({ queryKey: ["admin", "configuration"] }); toast.success(`${labels[item.key]?.title ?? item.key} updated`); }, onError: (error) => toast.error(toUiError(error).message) });
  return <AdminShell><div className="mx-auto max-w-6xl"><OperationsHeader kicker="System configuration" title="Operations without source edits." description="Validated values are cached in Redis, invalidated after updates, consumed centrally and written to the audit log." />
    {settings.isLoading ? <LoadingState className="mt-6" title="Loading operational settings" /> : null}{settings.isError ? <ErrorState className="mt-6" title={toUiError(settings.error).title} message={toUiError(settings.error).message} /> : null}
    {settings.data ? <Panel title="Runtime controls" detail="Unsafe values are rejected by typed backend bounds."><div className="grid gap-4 p-4 md:grid-cols-2">{settings.data.map((item) => { const meta = labels[item.key]; const Icon = meta?.icon ?? Settings2; return <article className="rounded-xl border border-border p-4" key={item.key}><div className="flex items-start gap-3"><span className="grid size-10 place-items-center rounded-xl bg-secondary"><Icon className="size-5" /></span><div><h3 className="text-lg font-bold">{meta?.title ?? item.key}</h3><p className="mt-1 text-xs leading-5 text-muted-foreground">{item.description}</p></div></div><div className="mt-4 flex items-center gap-2"><input className="h-11 min-w-0 flex-1 rounded-lg border border-input px-3" type="number" value={values[item.key] ?? item.value} onChange={(event) => setValues((current) => ({ ...current, [item.key]: Number(event.target.value) }))} /><span className="min-w-16 text-xs font-bold text-muted-foreground">{meta?.unit}</span><Button variant="outline" disabled={update.isPending || values[item.key] === item.value} onClick={() => update.mutate({ key: item.key, value: values[item.key] })}>Save</Button></div></article>; })}</div></Panel> : null}
  </div></AdminShell>;
}
