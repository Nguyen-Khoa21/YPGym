import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Search } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { DataTable } from "@/components/operations/DataTable";
import { Modal, Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { gymMarker } from "@/features/operations/gymScope";
import type { useOperationsScope } from "@/features/operations/useOperationsScope";
import { apiRequest } from "@/lib/apiClient";
import { ApiError, toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { AttendancePage, AttendanceSession } from "@/types/operations";

type AttendanceFilters = { member: string; status: string; dateFrom: string; dateTo: string };

const emptyFilters: AttendanceFilters = { member: "", status: "", dateFrom: "", dateTo: "" };

/**
 * Attendance sessions with filters and the audited manual-close dialog.
 * Shared by the manager attendance page and the staff workspace; the server still scopes by gym and shift.
 */
export function AttendanceSessionsPanel({ scope, enabled, onShiftRequired }: { scope: ReturnType<typeof useOperationsScope>; enabled: boolean; onShiftRequired: () => void }) {
  const { token } = useAuth();
  const [filters, setFilters] = useState(emptyFilters);
  const [applied, setApplied] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [closing, setClosing] = useState<AttendanceSession | null>(null);
  const [reason, setReason] = useState("");
  const marker = gymMarker(scope.gymId);
  const query = new URLSearchParams({ page: String(page), page_size: "25" });
  if (scope.gymParam) query.set("gym_id", scope.gymParam);
  if (applied.member) query.set("member", applied.member);
  if (applied.status) query.set("status", applied.status);
  if (applied.dateFrom) query.set("date_from", new Date(applied.dateFrom).toISOString());
  if (applied.dateTo) query.set("date_to", new Date(applied.dateTo).toISOString());
  const sessions = useQuery({ queryKey: ["attendance", "admin", marker, query.toString()], queryFn: ({ signal }) => apiRequest<AttendancePage>(`/attendance/admin?${query}`, { token, signal }), enabled: enabled });
  const shiftRequired = sessions.error instanceof ApiError && sessions.error.code === "SHIFT_REQUIRED";
  useEffect(() => {
    if (shiftRequired) onShiftRequired();
  }, [shiftRequired, onShiftRequired]);
  const manualClose = useMutation({
    mutationFn: ({ id, closeReason }: { id: string; closeReason: string }) => apiRequest<AttendanceSession>(`/attendance/admin/${id}/manual-close`, { method: "POST", token, body: { reason: closeReason } }),
    onSuccess: async (closed) => { setClosing(null); setReason(""); await Promise.all([queryClient.invalidateQueries({ queryKey: ["attendance", "admin"] }), queryClient.invalidateQueries({ queryKey: ["attendance", "crowdedness"] }), queryClient.invalidateQueries({ queryKey: ["attendance", "traffic-summary"] }), queryClient.invalidateQueries({ queryKey: ["attendance", "analytics-summary"] })]); if (closed.status === "manual_closed") toast.success("Attendance session closed"); else toast.info("That session was already closed. The list has been refreshed."); },
    onError: (error) => { if (error instanceof ApiError && error.code === "SHIFT_REQUIRED") onShiftRequired(); else toast.error(toUiError(error).message); },
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
  return <>
    <Panel title="Attendance sessions" detail="Filters run on PostgreSQL and manual closure always requires a reason."><form className="ops-toolbar" onSubmit={(event) => { event.preventDefault(); setApplied(filters); setPage(1); }}><Search className="size-4 text-muted-foreground" /><input aria-label="Search attendance member" placeholder="Member name or email" value={filters.member} onChange={(event) => setFilters((current) => ({ ...current, member: event.target.value }))} /><select aria-label="Filter attendance status" value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">All statuses</option><option value="active">Active</option><option value="checked_out">Checked out</option><option value="timed_out">Timed out</option><option value="manual_closed">Manual closed</option></select><input aria-label="Attendance from" type="datetime-local" value={filters.dateFrom} onChange={(event) => setFilters((current) => ({ ...current, dateFrom: event.target.value }))} /><input aria-label="Attendance to" type="datetime-local" value={filters.dateTo} onChange={(event) => setFilters((current) => ({ ...current, dateTo: event.target.value }))} /><Button type="submit" variant="secondary">Apply</Button></form>
      {sessions.isLoading ? <LoadingState className="m-4" title="Loading attendance operations" /> : null}{sessions.isError ? <ErrorState className="m-4" title={toUiError(sessions.error).title} message={toUiError(sessions.error).message} action={<Button variant="outline" onClick={() => sessions.refetch()}>Retry</Button>} /> : null}{sessions.data?.items.length === 0 ? <EmptyState className="m-4" title="No attendance sessions match" message="Adjust the member, status, or date filters." /> : null}{sessions.data?.items.length ? <><DataTable columns={columns} data={sessions.data.items} getRowId={(row) => row.id} label="Attendance session results" /><Pagination page={page} pages={sessions.data.page.pages} total={sessions.data.page.total} onPage={setPage} /></> : null}
    </Panel>
    {closing ? <Modal error={(manualClose).isError ? toUiError((manualClose).error).message : undefined} title="Manually close attendance session" description={`${closing.member_name ?? "Member"} checked in ${formatDateTime(closing.checked_in_at)}.`} onClose={() => { setClosing(null); setReason(""); }}><div className="ops-modal__body"><label>Mandatory closure reason<textarea value={reason} onChange={(event) => setReason(event.target.value)} /></label><div className="ops-modal__actions"><Button variant="outline" onClick={() => { setClosing(null); setReason(""); }}>Cancel</Button><Button variant="danger" disabled={reason.trim().length < 10 || manualClose.isPending} onClick={() => manualClose.mutate({ id: closing.id, closeReason: reason.trim() })}>Close active session</Button></div></div></Modal> : null}
  </>;
}
