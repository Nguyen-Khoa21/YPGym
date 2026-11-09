import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Activity, Clock3, LogIn, LogOut, Search, ShieldCheck, UsersRound } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { DataTable } from "@/components/operations/DataTable";
import { MetricCard, Modal, OperationsHeader, Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { GymScopeBar } from "@/features/operations/components/GymScopeBar";
import { gymMarker } from "@/features/operations/gymScope";
import { useOperationsScope } from "@/features/operations/useOperationsScope";
import { apiRequest } from "@/lib/apiClient";
import { ApiError, toUiError } from "@/lib/apiErrors";
import { formatDateTime, formatMoney } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { AnalyticsSummary, AttendancePage, AttendanceSession, Crowdedness, MyStaffShifts, StaffShift, TrafficSummary } from "@/types/operations";

type AttendanceFilters = { member: string; status: string; dateFrom: string; dateTo: string };

const emptyFilters: AttendanceFilters = { member: "", status: "", dateFrom: "", dateTo: "" };

export function AdminAttendancePage() {
  const { token, user } = useAuth();
  const [filters, setFilters] = useState(emptyFilters);
  const [applied, setApplied] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [closing, setClosing] = useState<AttendanceSession | null>(null);
  const [reason, setReason] = useState("");
  const scope = useOperationsScope();
  const isStaff = user?.role === "staff";
  const shift = useQuery({ queryKey: ["staff", "shifts", "me", user?.id], queryFn: ({ signal }) => apiRequest<MyStaffShifts>("/staff/shifts/me", { token, signal }), enabled: isStaff });
  const marker = gymMarker(scope.gymId);
  const query = new URLSearchParams({ page: String(page), page_size: "25" });
  if (scope.gymParam) query.set("gym_id", scope.gymParam);
  if (applied.member) query.set("member", applied.member);
  if (applied.status) query.set("status", applied.status);
  if (applied.dateFrom) query.set("date_from", new Date(applied.dateFrom).toISOString());
  if (applied.dateTo) query.set("date_to", new Date(applied.dateTo).toISOString());
  const gymQuery = scope.gymParam ? `?gym_id=${encodeURIComponent(scope.gymParam)}` : "";
  const canViewAnalytics = user?.role === "manager" || user?.role === "admin";
  const shiftOpen = !isStaff || Boolean(shift.data?.open_shift);
  const [closeRejected, setCloseRejected] = useState(false);
  // Staff may only use attendance while clocked in. Nothing is requested while locked.
    const unlocked = scope.ready && shiftOpen && !closeRejected;
  const sessions = useQuery({ queryKey: ["attendance", "admin", marker, query.toString()], queryFn: ({ signal }) => apiRequest<AttendancePage>(`/attendance/admin?${query}`, { token, signal }), enabled: unlocked });
  const crowdedness = useQuery({ queryKey: ["attendance", "crowdedness", marker], queryFn: ({ signal }) => apiRequest<Crowdedness>(`/attendance/crowdedness${gymQuery}`, { token, signal }), refetchInterval: 30_000, enabled: unlocked && Boolean(scope.gymId) });
  const traffic = useQuery({ queryKey: ["attendance", "traffic-summary", marker], queryFn: ({ signal }) => apiRequest<TrafficSummary>(`/admin/analytics/traffic-summary${gymQuery}`, { token, signal }), enabled: canViewAnalytics && unlocked && Boolean(scope.gymId), staleTime: 300_000 });
  const summary = useQuery({ queryKey: ["attendance", "analytics-summary", marker], queryFn: ({ signal }) => apiRequest<AnalyticsSummary>(`/admin/analytics/summary${gymQuery}`, { token, signal }), enabled: canViewAnalytics && unlocked, staleTime: 60_000, refetchInterval: 60_000 });
  const shiftRequired = sessions.error instanceof ApiError && sessions.error.code === "SHIFT_REQUIRED";
  const shiftRefetch = shift.refetch;
  useEffect(() => {
    if (shiftRequired || closeRejected) void shiftRefetch();
  }, [shiftRequired, closeRejected, shiftRefetch]);
  const clock = useMutation({
    mutationFn: (action: "clock-in" | "clock-out") => apiRequest<StaffShift>(`/staff/shifts/${action}`, { method: "POST", token }),
    onSuccess: async (_, action) => {
      setCloseRejected(false);
      // Update the shift first so the workspace locks before cached attendance data is discarded.
      await queryClient.invalidateQueries({ queryKey: ["staff", "shifts"] });
      queryClient.removeQueries({ queryKey: ["attendance", "admin"] });
      toast.success(action === "clock-in" ? "Clocked in" : "Clocked out");
    },
    onError: (error) => toast.error(toUiError(error).message),
  });
  const manualClose = useMutation({
    mutationFn: ({ id, closeReason }: { id: string; closeReason: string }) => apiRequest<AttendanceSession>(`/attendance/admin/${id}/manual-close`, { method: "POST", token, body: { reason: closeReason } }),
    onSuccess: async (closed) => { setClosing(null); setReason(""); await Promise.all([queryClient.invalidateQueries({ queryKey: ["attendance", "admin"] }), queryClient.invalidateQueries({ queryKey: ["attendance", "crowdedness"] }), queryClient.invalidateQueries({ queryKey: ["attendance", "traffic-summary"] }), queryClient.invalidateQueries({ queryKey: ["attendance", "analytics-summary"] })]); if (closed.status === "manual_closed") toast.success("Attendance session closed"); else toast.info("That session was already closed. The list has been refreshed."); },
    onError: (error) => { if (error instanceof ApiError && error.code === "SHIFT_REQUIRED") setCloseRejected(true); else toast.error(toUiError(error).message); },
  });
  const columns: ColumnDef<AttendanceSession>[] = [
    { header: "Member", cell: ({ row }) => <div><strong>{row.original.member_name ?? row.original.user_id.slice(0, 8)}</strong><p className="mt-1 text-[11px] text-muted-foreground">{row.original.member_email}</p></div> },
    ...(scope.isOwner && !scope.gymId ? [{ header: "Gym", cell: ({ row }: { row: { original: AttendanceSession } }) => scope.gyms.find((gym) => gym.id === row.original.gym_id)?.name ?? "-" }] : []),
    { header: "Check-in", cell: ({ row }) => formatDateTime(row.original.checked_in_at) },
    { header: "Closed", cell: ({ row }) => row.original.closed_at ? formatDateTime(row.original.closed_at) : "-" },
    { header: "Status", cell: ({ row }) => <StatusBadge value={row.original.status} /> },
    { header: "Device / source", cell: ({ row }) => <div><strong>{row.original.device_id ?? "No device"}</strong><p className="mt-1 text-[11px] text-muted-foreground">{row.original.source}</p></div> },
    { header: "Action", cell: ({ row }) => row.original.status === "active" ? <Button variant="outline" onClick={() => setClosing(row.original)}>Manual close</Button> : <span className="text-xs text-muted-foreground">Closed</span> },
  ];
  if (isStaff && shift.isLoading) return <AdminShell><LoadingState className="m-4" title="Checking your shift" /></AdminShell>;
  if (isStaff && (!shiftOpen || shiftRequired || closeRejected)) return <AdminShell><div className="mx-auto max-w-3xl">
    <OperationsHeader kicker="Attendance operations" title="Clock in to start." description="Attendance tools open only while you are on shift at your gym." />
    <GymScopeBar scope={scope} />
    <Panel title="You are clocked out" detail={scope.gymName ? `Gym: ${scope.gymName}` : "Loading your gym"}><div className="p-5"><p className="text-sm text-muted-foreground">No attendance or occupancy data is loaded until you clock in.</p><Button className="mt-4" disabled={clock.isPending} onClick={() => clock.mutate("clock-in")}><LogIn className="size-4" /> Clock in</Button>{shift.isError ? <p className="mt-3 text-sm text-destructive">{toUiError(shift.error).message}</p> : null}</div></Panel>
  </div></AdminShell>;
  return <AdminShell><div className="mx-auto max-w-7xl">
    <OperationsHeader kicker="Attendance operations" title="Live occupancy, permanent evidence." description="The dashboard combines current capacity, persisted sessions, closure controls, and previous-month occupancy estimates." actions={isStaff && shift.data?.open_shift ? <Button variant="outline" disabled={clock.isPending} onClick={() => clock.mutate("clock-out")}><LogOut className="size-4" /> Clock out</Button> : undefined} />
    <GymScopeBar scope={scope} />
    {isStaff && shift.data?.open_shift ? <p className="mb-4 text-sm text-muted-foreground">On shift since {formatDateTime(shift.data.open_shift.clocked_in_at, shift.data.gym_timezone)}.</p> : null}
    {scope.error ? <ErrorState className="mb-5" title={toUiError(scope.error).title} message={toUiError(scope.error).message} action={<Button variant="outline" onClick={scope.retry}>Retry</Button>} /> : null}
    {scope.isOwner && scope.ready && !scope.gymId ? <p className="mb-4 rounded-lg border border-border bg-muted/50 p-3 text-sm">Showing all branches. Choose one branch to see its live occupancy and traffic. Percentages of different gyms are never combined.</p> : null}
    <div className="ops-metrics"><MetricCard label="Active occupancy" value={crowdedness.data?.active_count ?? "-"} tone="forest" detail={crowdedness.data ? `${crowdedness.data.capacity} capacity` : scope.gymId ? "Loading facility count" : "Choose a branch"} /><MetricCard label="Capacity used" value={crowdedness.data ? `${crowdedness.data.percentage}%` : "-"} tone="lime" /><MetricCard label="Facility status" value={crowdedness.data?.status ?? "Checking"} /><MetricCard label="Previous-month visits" value={traffic.data?.visits ?? "Role restricted"} tone="coral" detail={traffic.data?.data_sufficient ? `${traffic.data.unique_members} unique members` : "Manager/admin analytics"} /></div>
    {crowdedness.isError ? <ErrorState className="mb-5" title={toUiError(crowdedness.error).title} message={toUiError(crowdedness.error).message} /> : null}
    <Panel title="Attendance sessions" detail="Filters run on PostgreSQL and manual closure always requires a reason."><form className="ops-toolbar" onSubmit={(event) => { event.preventDefault(); setApplied(filters); setPage(1); }}><Search className="size-4 text-muted-foreground" /><input aria-label="Search attendance member" placeholder="Member name or email" value={filters.member} onChange={(event) => setFilters((current) => ({ ...current, member: event.target.value }))} /><select aria-label="Filter attendance status" value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">All statuses</option><option value="active">Active</option><option value="checked_out">Checked out</option><option value="timed_out">Timed out</option><option value="manual_closed">Manual closed</option></select><input aria-label="Attendance from" type="datetime-local" value={filters.dateFrom} onChange={(event) => setFilters((current) => ({ ...current, dateFrom: event.target.value }))} /><input aria-label="Attendance to" type="datetime-local" value={filters.dateTo} onChange={(event) => setFilters((current) => ({ ...current, dateTo: event.target.value }))} /><Button type="submit" variant="secondary">Apply</Button></form>
      {sessions.isLoading ? <LoadingState className="m-4" title="Loading attendance operations" /> : null}{sessions.isError ? <ErrorState className="m-4" title={toUiError(sessions.error).title} message={toUiError(sessions.error).message} action={<Button variant="outline" onClick={() => sessions.refetch()}>Retry</Button>} /> : null}{sessions.data?.items.length === 0 ? <EmptyState className="m-4" title="No attendance sessions match" message="Adjust the member, status, or date filters." /> : null}{sessions.data?.items.length ? <><DataTable columns={columns} data={sessions.data.items} getRowId={(row) => row.id} label="Attendance session results" /><Pagination page={page} pages={sessions.data.page.pages} total={sessions.data.page.total} onPage={setPage} /></> : null}
    </Panel>
    <div className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
      <Panel title="Previous-month traffic" detail={canViewAnalytics ? "Average concurrent occupancy sampled every 15 minutes and grouped into two-hour local-time windows." : "Manager/admin analytics are intentionally hidden from staff."}><TrafficPanel query={traffic} canView={canViewAnalytics} /></Panel>
      <Panel title="Control boundaries" detail="Role-aware operational safeguards."><div className="grid gap-3 p-4"><Control icon={UsersRound} title="Member isolation" detail="Members can retrieve only their own attendance history." /><Control icon={ShieldCheck} title="Reason required" detail="Staff, managers, and admins can close abnormal active sessions only with an audit reason." /><Control icon={Clock3} title="Timeout worker" detail="Celery Beat reconciles sessions older than the configured timeout." /><Control icon={Activity} title="Database truth" detail="Occupancy is rebuilt from active PostgreSQL sessions when the cache is absent or stale." /></div></Panel>
    </div>
    {canViewAnalytics ? <AnalyticsSummaryPanel query={summary} /> : null}
    {closing ? <Modal error={(manualClose).isError ? toUiError((manualClose).error).message : undefined} title="Manually close attendance session" description={`${closing.member_name ?? "Member"} checked in ${formatDateTime(closing.checked_in_at)}.`} onClose={() => { setClosing(null); setReason(""); }}><div className="ops-modal__body"><label>Mandatory closure reason<textarea value={reason} onChange={(event) => setReason(event.target.value)} /></label><div className="ops-modal__actions"><Button variant="outline" onClick={() => { setClosing(null); setReason(""); }}>Cancel</Button><Button variant="danger" disabled={reason.trim().length < 10 || manualClose.isPending} onClick={() => manualClose.mutate({ id: closing.id, closeReason: reason.trim() })}>Close active session</Button></div></div></Modal> : null}
  </div></AdminShell>;
}

function AnalyticsSummaryPanel({ query }: { query: ReturnType<typeof useQuery<AnalyticsSummary>> }) {
  if (query.isLoading) return <Panel className="mt-5" title="Manager summary" detail="Membership, class, attendance, and revenue aggregates are calculated from persisted records."><LoadingState className="m-4" title="Aggregating manager summary" /></Panel>;
  if (query.isError) return <Panel className="mt-5" title="Manager summary" detail="The analytics summary could not be loaded."><ErrorState className="m-4" title={toUiError(query.error).title} message={toUiError(query.error).message} action={<Button variant="outline" onClick={() => query.refetch()}>Retry</Button>} /></Panel>;
  if (!query.data) return null;
  const data = query.data;
  return <Panel className="mt-5" title="Manager summary" detail={`Last 30 days through ${formatDateTime(data.date_to)}. Checks for updates every minute; generated ${formatDateTime(data.generated_at)}.`}>
    <div className="ops-metrics p-4">{data.revenue ? <MetricCard label="Successful payments" value={data.revenue.successful_payments} tone="coral" detail={formatMoney(data.revenue.gross_amount)} /> : <MetricCard label="Class bookings" value={data.class_popularity.reduce((total, item) => total + item.bookings, 0)} tone="coral" detail="Last 30 days, this gym" />}<MetricCard label="Check-ins" value={data.attendance.check_ins} tone="forest" detail={`${data.attendance.unique_members} unique members`} /><MetricCard label="Average visit" value={data.attendance.average_visit_minutes === null ? "-" : `${data.attendance.average_visit_minutes} min`} tone="lime" detail={data.attendance.busiest_slot ?? "No peak slot"} />{data.revenue ? <MetricCard label="Discounts" value={formatMoney(data.revenue.discounts)} /> : <MetricCard label="Memberships created" value={data.membership_trends.reduce((total, item) => total + item.total, 0)} detail="Last 30 days, this gym" />}</div>
    <div className="grid gap-5 border-t border-border p-4 xl:grid-cols-2">
      <div><h3 className="text-sm font-semibold">Memberships created by month (UTC)</h3><p className="mt-1 text-xs text-muted-foreground">Current status of memberships created in each month; renewals update the existing membership.</p><div className="mt-3 overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr className="border-b border-border text-muted-foreground"><th className="pb-2">Month</th><th className="pb-2">Total</th><th className="pb-2">Active</th><th className="pb-2">Frozen</th><th className="pb-2">Expired</th></tr></thead><tbody>{data.membership_trends.map((point) => <tr className="border-b border-border/60" key={point.period}><td className="py-2">{new Intl.DateTimeFormat("en-MY", { month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${point.period}T00:00:00Z`))}</td><td>{point.total}</td><td>{point.active}</td><td>{point.frozen}</td><td>{point.expired}</td></tr>)}</tbody></table></div></div>
      <div><h3 className="text-sm font-semibold">Class popularity</h3><div className="mt-3 overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr className="border-b border-border text-muted-foreground"><th className="pb-2">Type</th><th className="pb-2">Bookings</th><th className="pb-2">Unique members</th><th className="pb-2">Use</th></tr></thead><tbody>{data.class_popularity.map((point) => <tr className="border-b border-border/60" key={point.class_type}><td className="py-2">{point.class_type}</td><td>{point.bookings}</td><td>{point.unique_members}</td><td>{point.utilization_percent}%</td></tr>)}</tbody></table>{data.class_popularity.length === 0 ? <p className="mt-3 text-xs text-muted-foreground">No classes were scheduled in this range.</p> : null}</div></div>
    </div>
  </Panel>;
}

function TrafficPanel({ query, canView }: { query: ReturnType<typeof useQuery<TrafficSummary>>; canView: boolean }) {
  if (!canView) return <EmptyState className="m-4" title="Operational access only" message="Staff can manage attendance sessions but cannot view manager analytics." />;
  if (query.isLoading) return <LoadingState className="m-4" title="Estimating previous-month occupancy" />;
  if (query.isError) return <ErrorState className="m-4" title={toUiError(query.error).title} message={toUiError(query.error).message} action={<Button variant="outline" onClick={() => query.refetch()}>Retry</Button>} />;
  if (!query.data) return null;
  const data = query.data;
  if (!data.data_sufficient) return <EmptyState className="m-4" title="Not enough attendance data yet" message={`At least ${data.methodology.minimum_sessions} overlapping sessions are required before busiest or quietest windows are shown.`} />;
  return <div>
    <div className="ops-metrics p-4">
      <MetricCard label="Busiest window" value={data.busiest_window?.label ?? "-"} tone="coral" detail={data.busiest_window ? `${data.busiest_window.average_capacity_percentage}% average capacity` : undefined} />
      <MetricCard label="Quietest window" value={data.quietest_window?.label ?? "-"} tone="lime" detail={data.quietest_window ? `${data.quietest_window.average_capacity_percentage}% average capacity` : undefined} />
      <MetricCard label="Average occupancy" value={`${data.average_capacity_percentage}%`} tone="forest" detail={`${data.average_headcount} average members`} />
      <MetricCard label="Average visit" value={data.average_visit_minutes === null ? "-" : `${data.average_visit_minutes} min`} detail={`${data.visits} visits · ${data.unique_members} members`} />
    </div>
    {data.contains_demo_data ? <p className="mx-4 mb-3 rounded-lg border border-secondary/50 bg-secondary/10 p-3 text-xs font-semibold">This summary includes synthetic demo attendance.</p> : null}
    <TrafficHeatmap data={data} />
    <p className="px-4 pb-4 text-xs leading-5 text-muted-foreground">Historical estimate, not a prediction. The previous completed month uses {data.timezone}, {data.methodology.sample_interval_minutes}-minute samples, and two-hour windows. {data.methodology.session_end_rule}</p>
  </div>;
}

function TrafficHeatmap({ data }: { data: TrafficSummary }) {
  const maximum = Math.max(0, ...data.weekday_buckets.map((cell) => cell.average_capacity_percentage));
  const rows = Array.from({ length: 7 }, (_, weekday) => data.weekday_buckets.filter((cell) => cell.weekday === weekday));
  return <div className="heatmap-wrap"><div className="attendance-heatmap attendance-heatmap--traffic" role="grid" aria-label="Previous-month average occupancy heatmap"><div className="heatmap-row heatmap-row--header" role="row"><span role="columnheader">Day</span>{data.buckets.map((bucket) => <span role="columnheader" key={bucket.start_hour}>{bucket.start_hour.toString().padStart(2, "0")}</span>)}</div>{rows.map((row, weekday) => <div className="heatmap-row" role="row" key={weekday}><strong role="rowheader">{row[0]?.weekday_label.slice(0, 3)}</strong>{row.map((cell) => { const intensity = maximum ? cell.average_capacity_percentage / maximum : 0; const tone = cell.average_capacity_percentage === 0 ? "empty" : intensity <= 0.33 ? "low" : intensity <= 0.66 ? "medium" : "high"; const description = `${cell.weekday_label}, ${cell.label}: ${cell.average_headcount} average members, ${cell.average_capacity_percentage}% capacity`; return <span className={`heatmap-cell heatmap-cell--${tone}`} role="gridcell" aria-label={description} title={description} key={cell.start_hour}>{cell.average_capacity_percentage}%</span>; })}</div>)}</div><div className="overflow-x-auto px-4 pb-4"><table className="w-full text-left text-xs"><caption className="sr-only">Two-hour average occupancy text alternative</caption><thead><tr className="border-b border-border text-muted-foreground"><th className="pb-2">Window</th><th className="pb-2">Average members</th><th className="pb-2">Capacity used</th></tr></thead><tbody>{data.buckets.map((bucket) => <tr className="border-b border-border/60" key={bucket.start_hour}><td className="py-2">{bucket.label}</td><td>{bucket.average_headcount}</td><td>{bucket.average_capacity_percentage}%</td></tr>)}</tbody></table></div></div>;
}

function Control({ icon: Icon, title, detail }: { icon: typeof Activity; title: string; detail: string }) { return <article className="rounded-xl border border-border p-4"><Icon className="size-5 text-primary" /><strong className="mt-3 block text-sm">{title}</strong><p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p></article>; }
