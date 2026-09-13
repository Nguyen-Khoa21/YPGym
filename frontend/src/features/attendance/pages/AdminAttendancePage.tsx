import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Activity, Clock3, Search, ShieldCheck, UsersRound } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { DataTable } from "@/components/operations/DataTable";
import { MetricCard, Modal, OperationsHeader, Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { AttendancePage, AttendanceSession, Crowdedness, PeakHours } from "@/types/operations";

type AttendanceFilters = { member: string; status: string; dateFrom: string; dateTo: string };

const emptyFilters: AttendanceFilters = { member: "", status: "", dateFrom: "", dateTo: "" };

export function AdminAttendancePage() {
  const { token, user } = useAuth();
  const [filters, setFilters] = useState(emptyFilters);
  const [applied, setApplied] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [closing, setClosing] = useState<AttendanceSession | null>(null);
  const [reason, setReason] = useState("");
  const query = new URLSearchParams({ page: String(page), page_size: "25" });
  if (applied.member) query.set("member", applied.member);
  if (applied.status) query.set("status", applied.status);
  if (applied.dateFrom) query.set("date_from", new Date(applied.dateFrom).toISOString());
  if (applied.dateTo) query.set("date_to", new Date(applied.dateTo).toISOString());
  const sessions = useQuery({ queryKey: ["attendance", "admin", query.toString()], queryFn: ({ signal }) => apiRequest<AttendancePage>(`/attendance/admin?${query}`, { token, signal }) });
  const crowdedness = useQuery({ queryKey: ["attendance", "crowdedness"], queryFn: ({ signal }) => apiRequest<Crowdedness>("/attendance/crowdedness", { token, signal }), refetchInterval: 30_000 });
  const canViewAnalytics = user?.role === "manager" || user?.role === "admin";
  const analytics = useQuery({ queryKey: ["attendance", "peak-hours"], queryFn: ({ signal }) => apiRequest<PeakHours>("/admin/analytics/peak-hours", { token, signal }), enabled: canViewAnalytics });
  const manualClose = useMutation({
    mutationFn: ({ id, closeReason }: { id: string; closeReason: string }) => apiRequest<AttendanceSession>(`/attendance/admin/${id}/manual-close`, { method: "POST", token, body: { reason: closeReason } }),
    onSuccess: async () => { setClosing(null); setReason(""); await Promise.all([queryClient.invalidateQueries({ queryKey: ["attendance", "admin"] }), queryClient.invalidateQueries({ queryKey: ["attendance", "crowdedness"] }), queryClient.invalidateQueries({ queryKey: ["attendance", "peak-hours"] })]); toast.success("Attendance session closed"); },
    onError: (error) => toast.error(toUiError(error).message),
  });
  const columns: ColumnDef<AttendanceSession>[] = [
    { header: "Member", cell: ({ row }) => <div><strong>{row.original.member_name ?? row.original.user_id.slice(0, 8)}</strong><p className="mt-1 text-[11px] text-muted-foreground">{row.original.member_email}</p></div> },
    { header: "Check-in", cell: ({ row }) => formatDateTime(row.original.checked_in_at) },
    { header: "Closed", cell: ({ row }) => row.original.closed_at ? formatDateTime(row.original.closed_at) : "-" },
    { header: "Status", cell: ({ row }) => <StatusBadge value={row.original.status} /> },
    { header: "Device / source", cell: ({ row }) => <div><strong>{row.original.device_id ?? "No device"}</strong><p className="mt-1 text-[11px] text-muted-foreground">{row.original.source}</p></div> },
    { header: "Action", cell: ({ row }) => row.original.status === "active" ? <Button variant="outline" onClick={() => setClosing(row.original)}>Manual close</Button> : <span className="text-xs text-muted-foreground">Closed</span> },
  ];
  return <AdminShell><div className="mx-auto max-w-7xl">
    <OperationsHeader kicker="Attendance operations" title="Live occupancy, permanent evidence." description="The dashboard combines current capacity, persisted sessions, device sources, closure controls, and peak-hour analysis." />
    <div className="ops-metrics"><MetricCard label="Active occupancy" value={crowdedness.data?.active_count ?? "-"} tone="forest" detail={crowdedness.data ? `${crowdedness.data.capacity} capacity` : "Loading facility count"} /><MetricCard label="Capacity used" value={crowdedness.data ? `${crowdedness.data.percentage}%` : "-"} tone="lime" /><MetricCard label="Facility status" value={crowdedness.data?.status ?? "Checking"} /><MetricCard label="Visits today" value={analytics.data?.visits_today ?? "Role restricted"} tone="coral" detail={analytics.data?.busiest_hour ?? "Manager/admin analytics"} /></div>
    {crowdedness.isError ? <ErrorState className="mb-5" title={toUiError(crowdedness.error).title} message={toUiError(crowdedness.error).message} /> : null}
    <Panel title="Attendance sessions" detail="Filters run on PostgreSQL and manual closure always requires a reason."><form className="ops-toolbar" onSubmit={(event) => { event.preventDefault(); setApplied(filters); setPage(1); }}><Search className="size-4 text-muted-foreground" /><input aria-label="Search attendance member" placeholder="Member name or email" value={filters.member} onChange={(event) => setFilters((current) => ({ ...current, member: event.target.value }))} /><select aria-label="Filter attendance status" value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">All statuses</option><option value="active">Active</option><option value="checked_out">Checked out</option><option value="timed_out">Timed out</option><option value="manual_closed">Manual closed</option></select><input aria-label="Attendance from" type="datetime-local" value={filters.dateFrom} onChange={(event) => setFilters((current) => ({ ...current, dateFrom: event.target.value }))} /><input aria-label="Attendance to" type="datetime-local" value={filters.dateTo} onChange={(event) => setFilters((current) => ({ ...current, dateTo: event.target.value }))} /><Button type="submit" variant="secondary">Apply</Button></form>
      {sessions.isLoading ? <LoadingState className="m-4" title="Loading attendance operations" /> : null}{sessions.isError ? <ErrorState className="m-4" title={toUiError(sessions.error).title} message={toUiError(sessions.error).message} action={<Button variant="outline" onClick={() => sessions.refetch()}>Retry</Button>} /> : null}{sessions.data?.items.length === 0 ? <EmptyState className="m-4" title="No attendance sessions match" message="Adjust the member, status, or date filters." /> : null}{sessions.data?.items.length ? <><DataTable columns={columns} data={sessions.data.items} getRowId={(row) => row.id} label="Attendance session results" /><Pagination page={page} pages={sessions.data.page.pages} total={sessions.data.page.total} onPage={setPage} /></> : null}
    </Panel>
    <div className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
      <Panel title="Peak-hours heatmap" detail={canViewAnalytics ? "Weekday-by-hour check-ins for the last 30 days." : "Manager/admin analytics are intentionally hidden from staff."}>{analytics.isLoading ? <LoadingState className="m-4" title="Aggregating peak hours" /> : null}{analytics.isError ? <ErrorState className="m-4" title={toUiError(analytics.error).title} message={toUiError(analytics.error).message} /> : null}{analytics.data ? <PeakHoursGrid data={analytics.data} /> : null}{!canViewAnalytics ? <EmptyState className="m-4" title="Operational access only" message="Staff can manage attendance sessions but cannot view manager analytics." /> : null}</Panel>
      <Panel title="Control boundaries" detail="Role-aware operational safeguards."><div className="grid gap-3 p-4"><Control icon={UsersRound} title="Member isolation" detail="Members can retrieve only their own attendance history." /><Control icon={ShieldCheck} title="Reason required" detail="Staff, managers, and admins can close abnormal active sessions only with an audit reason." /><Control icon={Clock3} title="Timeout worker" detail="Celery Beat reconciles sessions older than the configured timeout." /><Control icon={Activity} title="Database truth" detail="Occupancy is rebuilt from active PostgreSQL sessions when the cache is absent or stale." /></div></Panel>
    </div>
    {closing ? <Modal error={(manualClose).isError ? toUiError((manualClose).error).message : undefined} title="Manually close attendance session" description={`${closing.member_name ?? "Member"} checked in ${formatDateTime(closing.checked_in_at)}.`} onClose={() => { setClosing(null); setReason(""); }}><div className="ops-modal__body"><label>Mandatory closure reason<textarea value={reason} onChange={(event) => setReason(event.target.value)} /></label><div className="ops-modal__actions"><Button variant="outline" onClick={() => { setClosing(null); setReason(""); }}>Cancel</Button><Button variant="danger" disabled={reason.trim().length < 10 || manualClose.isPending} onClick={() => manualClose.mutate({ id: closing.id, closeReason: reason.trim() })}>Close active session</Button></div></div></Modal> : null}
  </div></AdminShell>;
}

function PeakHoursGrid({ data }: { data: PeakHours }) {
  const maximum = Math.max(0, ...data.cells.map((cell) => cell.visits));
  const rows = Array.from({ length: 7 }, (_, weekday) => data.cells.filter((cell) => cell.weekday === weekday));
  return <div className="heatmap-wrap"><div className="attendance-heatmap" role="grid" aria-label="Peak-hour attendance heatmap"><div className="heatmap-row heatmap-row--header" role="row"><span role="columnheader">Day</span>{Array.from({ length: 24 }, (_, hour) => <span role="columnheader" key={hour}>{String(hour).padStart(2, "0")}</span>)}</div>{rows.map((row, weekday) => <div className="heatmap-row" role="row" key={weekday}><strong role="rowheader">{row[0]?.weekday_label.slice(0, 3)}</strong>{row.map((cell) => { const intensity = maximum ? cell.visits / maximum : 0; const tone = cell.visits === 0 ? "empty" : intensity <= 0.33 ? "low" : intensity <= 0.66 ? "medium" : "high"; return <span className={`heatmap-cell heatmap-cell--${tone}`} role="gridcell" aria-label={`${cell.weekday_label} ${String(cell.hour).padStart(2, "0")}:00, ${cell.visits} visits`} title={`${cell.weekday_label} ${String(cell.hour).padStart(2, "0")}:00 - ${cell.visits} visits`} key={cell.hour}>{cell.visits}</span>; })}</div>)}</div>{maximum === 0 ? <p className="p-4 text-sm text-muted-foreground">No check-ins occurred in this range; the complete zero-value grid is still returned.</p> : null}</div>;
}

function Control({ icon: Icon, title, detail }: { icon: typeof Activity; title: string; detail: string }) { return <article className="rounded-xl border border-border p-4"><Icon className="size-5 text-primary" /><strong className="mt-3 block text-sm">{title}</strong><p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p></article>; }
