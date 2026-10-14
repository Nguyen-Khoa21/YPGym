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
import { configurationDraftState, refreshManagementQueries } from "@/lib/managementMutations";
import { queryClient } from "@/lib/queryClient";
import type { ConfigurationItem } from "@/types/operations";

const labels: Record<string, { title: string; unit: string; icon: typeof Gauge; minimum: number; maximum: number }> = {
  gym_capacity: { title: "Gym capacity", unit: "people", icon: UsersRound, minimum: 1, maximum: 5000 },
  qr_token_ttl_seconds: { title: "QR token lifetime", unit: "seconds", icon: QrCode, minimum: 15, maximum: 300 },
  attendance_timeout_minutes: { title: "Attendance timeout", unit: "minutes", icon: TimerReset, minimum: 15, maximum: 1440 },
  duplicate_scan_window_seconds: { title: "Duplicate scan window", unit: "seconds", icon: RefreshCw, minimum: 1, maximum: 300 },
  class_cancellation_window_hours: { title: "Class cancellation window", unit: "hours", icon: Settings2, minimum: 0, maximum: 168 },
  class_reminder_lead_minutes: { title: "Class reminder lead time", unit: "minutes", icon: TimerReset, minimum: 5, maximum: 1440 },
  waitlist_size: { title: "Default waitlist limit", unit: "members", icon: Gauge, minimum: 0, maximum: 100 },
};

export function AdminSettingsPage() {
  const { token } = useAuth();
  const settings = useQuery({ queryKey: ["admin", "configuration"], queryFn: ({ signal }) => apiRequest<ConfigurationItem[]>("/admin/configuration", { token, signal }) });
  const [values, setValues] = useState<Record<string, string>>({});
  const update = useMutation({ mutationFn: ({ key, value }: { key: string; value: number }) => apiRequest<ConfigurationItem>(`/admin/configuration/${key}`, { method: "PATCH", token, body: { value } }), onSuccess: async (item) => { queryClient.setQueryData<ConfigurationItem[]>(["admin", "configuration"], (current) => current?.map((existing) => existing.key === item.key ? item : existing)); setValues((current) => { const next = { ...current }; delete next[item.key]; return next; }); await refreshManagementQueries(queryClient, "configuration"); toast.success(`${labels[item.key]?.title ?? item.key} updated`, { id: "configuration-update" }); }, onError: (error) => toast.error(toUiError(error).message, { id: "configuration-update" }) });
  return <AdminShell><div className="mx-auto max-w-6xl"><OperationsHeader kicker="System configuration" title="Operations without source edits." description="Validated values are cached in Redis, invalidated after updates, consumed centrally and written to the audit log." />
    {settings.isLoading ? <LoadingState className="mt-6" title="Loading operational settings" /> : null}{settings.isError ? <ErrorState className="mt-6" title={toUiError(settings.error).title} message={toUiError(settings.error).message} /> : null}
    {settings.data ? <Panel title="Runtime controls" detail="Unsafe values are rejected by typed backend bounds."><div className="grid gap-4 p-4 md:grid-cols-2">{settings.data.map((item) => { const meta = labels[item.key]; const Icon = meta?.icon ?? Settings2; const rawValue = values[item.key] ?? String(item.value); const draft = configurationDraftState(rawValue, item.value, meta.minimum, meta.maximum); const invalid = values[item.key] !== undefined && !draft.valid; return <article className="rounded-xl border border-border p-4" key={item.key}><div className="flex items-start gap-3"><span className="grid size-10 place-items-center rounded-xl bg-secondary"><Icon className="size-5" /></span><div><h3 className="text-lg font-bold">{meta.title}</h3><p className="mt-1 text-xs leading-5 text-muted-foreground">{item.description}</p></div></div><div className="mt-4 flex items-center gap-2"><input aria-label={meta.title} aria-invalid={invalid} className="h-11 min-w-0 flex-1 rounded-lg border border-input px-3" type="number" min={meta.minimum} max={meta.maximum} step="1" value={rawValue} onChange={(event) => setValues((current) => ({ ...current, [item.key]: event.target.value }))} /><span className="min-w-16 text-xs font-bold text-muted-foreground">{meta.unit}</span><Button variant="outline" disabled={update.isPending || !draft.changed} onClick={() => update.mutate({ key: item.key, value: draft.value })}>{update.isPending && update.variables?.key === item.key ? "Saving..." : "Save"}</Button></div>{invalid ? <p className="mt-2 text-xs text-destructive" role="alert">Enter a whole number from {meta.minimum} to {meta.maximum}.</p> : null}</article>; })}</div></Panel> : null}
  </div></AdminShell>;
}
