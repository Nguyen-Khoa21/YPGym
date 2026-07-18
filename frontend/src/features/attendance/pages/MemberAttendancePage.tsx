import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { CalendarClock, LogIn, LogOut, TimerReset } from "lucide-react";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { DataTable } from "@/components/operations/DataTable";
import { MetricCard, OperationsHeader, Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import type { AttendancePage, AttendanceSession } from "@/types/operations";

const columns: ColumnDef<AttendanceSession>[] = [
  { header: "Check-in", cell: ({ row }) => formatDateTime(row.original.checked_in_at) },
  { header: "Closed", cell: ({ row }) => row.original.closed_at ? formatDateTime(row.original.closed_at) : "Still in facility" },
  { header: "Status", cell: ({ row }) => <StatusBadge value={row.original.status} /> },
  { header: "Source", cell: ({ row }) => <div><strong>{row.original.device_id ?? row.original.source}</strong><p className="mt-1 text-[11px] text-muted-foreground">{row.original.events.length} recorded event{row.original.events.length === 1 ? "" : "s"}</p></div> },
];

export function MemberAttendancePage() {
  const { token } = useAuth();
  const [page, setPage] = useState(1);
  const history = useQuery({ queryKey: ["attendance", "me", page], queryFn: ({ signal }) => apiRequest<AttendancePage>(`/attendance/me?page=${page}&page_size=20`, { token, signal }) });
  const active = history.data?.items.filter((item) => item.status === "active").length ?? 0;
  const closed = history.data?.items.filter((item) => item.status === "checked_out").length ?? 0;
  const timedOut = history.data?.items.filter((item) => item.status === "timed_out").length ?? 0;
  return <MemberShell><div className="mx-auto max-w-6xl"><OperationsHeader kicker="Attendance history" title="Every visit, persisted." description="Check-ins, check-outs, timeouts, and staff-assisted closures are retained as session events." />
    {history.data ? <div className="ops-metrics"><MetricCard label="All visits" value={history.data.page.total} tone="forest" /><MetricCard label="Active now" value={active} tone="lime" /><MetricCard label="Checked out on page" value={closed} /><MetricCard label="Timed out on page" value={timedOut} tone="coral" /></div> : null}
    <Panel title="Visit log" detail="Only your own attendance sessions are available here.">{history.isLoading ? <LoadingState className="m-4" title="Loading attendance history" /> : null}{history.isError ? <ErrorState className="m-4" title={toUiError(history.error).title} message={toUiError(history.error).message} action={<Button variant="outline" onClick={() => history.refetch()}>Retry</Button>} /> : null}{history.data?.items.length === 0 ? <EmptyState className="m-4" title="No attendance sessions" message="Open My QR Code and scan at a registered device to record a visit." /> : null}{history.data?.items.length ? <><DataTable columns={columns} data={history.data.items} getRowId={(row) => row.id} label="Member attendance history" /><Pagination page={page} pages={history.data.page.pages} total={history.data.page.total} onPage={setPage} /></> : null}</Panel>
    <div className="mt-5 grid gap-3 sm:grid-cols-3"><Explainer icon={LogIn} title="Check-in" detail="Created only after token, device, membership, and duplicate checks pass." /><Explainer icon={LogOut} title="Check-out" detail="Closes the active session and immediately lowers occupancy." /><Explainer icon={TimerReset} title="Timeout" detail="The scheduled worker closes visits that exceed the configured limit." /></div>
  </div></MemberShell>;
}

function Explainer({ icon: Icon, title, detail }: { icon: typeof CalendarClock; title: string; detail: string }) { return <article className="surface-card p-4"><Icon className="size-5 text-primary" /><strong className="mt-3 block text-sm">{title}</strong><p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p></article>; }
