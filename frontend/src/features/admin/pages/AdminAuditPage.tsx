import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Search, ShieldCheck } from "lucide-react";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { DataTable } from "@/components/operations/DataTable";
import { MetricCard, OperationsHeader, Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import type { AuditItem, AuditPage } from "@/types/operations";

const columns: ColumnDef<AuditItem>[] = [
  { header: "Time", cell: ({ row }) => formatDateTime(row.original.created_at) },
  { header: "Action", cell: ({ row }) => <div><strong>{row.original.action}</strong><p className="mt-1 text-[11px] text-muted-foreground">{row.original.summary}</p></div> },
  { header: "Actor", cell: ({ row }) => row.original.actor_name ?? "System" },
  { header: "Target / entity", cell: ({ row }) => <div><strong>{row.original.target_name ?? row.original.entity_type}</strong><p className="mt-1 text-[11px] text-muted-foreground">{row.original.entity_type} {row.original.entity_id ? `· ${row.original.entity_id.slice(0, 8)}` : ""}</p></div> },
  { header: "Reason", cell: ({ row }) => row.original.reason ?? "-" },
  { header: "Outcome", cell: ({ row }) => row.original.outcome ? <StatusBadge value={row.original.outcome} /> : "-" },
];

export function AdminAuditPage() {
  const { token } = useAuth();
  const [filters, setFilters] = useState({ action: "", actor: "", target: "", entity: "", dateFrom: "", dateTo: "" });
  const [applied, setApplied] = useState(filters);
  const [page, setPage] = useState(1);
  const query = new URLSearchParams({ page: String(page), page_size: "25" });
  if (applied.action) query.set("action", applied.action);
  if (applied.actor) query.set("actor", applied.actor);
  if (applied.target) query.set("target", applied.target);
  if (applied.entity) query.set("entity", applied.entity);
  if (applied.dateFrom) query.set("date_from", `${applied.dateFrom}T00:00:00Z`);
  if (applied.dateTo) query.set("date_to", `${applied.dateTo}T23:59:59Z`);
  const logs = useQuery({ queryKey: ["admin", "audit", query.toString()], queryFn: ({ signal }) => apiRequest<AuditPage>(`/admin/audit-logs?${query}`, { token, signal }) });
  return <AdminShell><div className="mx-auto max-w-7xl"><OperationsHeader kicker="Governance" title="Every sensitive action leaves a trail." description="Manager and admin review for decisions, exports, configuration changes, broadcasts and operational closures." />
    {logs.data ? <div className="ops-metrics"><MetricCard label="Matching events" value={logs.data.page.total} tone="forest" /><MetricCard label="Current page" value={logs.data.page.page} tone="lime" /><MetricCard label="Secrets exposed" value="0" /><MetricCard label="Access" value="Restricted" tone="coral" /></div> : null}
    <Panel title="Audit log" detail="Newest events appear first and payloads omit passwords, API keys and token material."><form className="ops-toolbar" onSubmit={(event) => { event.preventDefault(); setApplied({ ...filters }); setPage(1); }}><Search className="size-4 text-muted-foreground" /><input aria-label="Filter audit action" placeholder="Action" value={filters.action} onChange={(event) => setFilters({ ...filters, action: event.target.value })} /><input aria-label="Filter audit actor" placeholder="Actor name or email" value={filters.actor} onChange={(event) => setFilters({ ...filters, actor: event.target.value })} /><input aria-label="Filter audit target" placeholder="Target name or email" value={filters.target} onChange={(event) => setFilters({ ...filters, target: event.target.value })} /><input aria-label="Filter audit entity" placeholder="Entity" value={filters.entity} onChange={(event) => setFilters({ ...filters, entity: event.target.value })} /><input aria-label="Audit date from" type="date" value={filters.dateFrom} onChange={(event) => setFilters({ ...filters, dateFrom: event.target.value })} /><input aria-label="Audit date to" type="date" value={filters.dateTo} onChange={(event) => setFilters({ ...filters, dateTo: event.target.value })} /><Button type="submit" variant="secondary">Apply</Button><span className="ml-auto flex items-center gap-2 text-xs font-bold text-muted-foreground"><ShieldCheck className="size-4" /> Manager/admin only</span></form>
      {logs.isLoading ? <LoadingState className="m-4" title="Loading audit records" /> : null}{logs.isError ? <ErrorState className="m-4" title={toUiError(logs.error).title} message={toUiError(logs.error).message} /> : null}{logs.data?.items.length === 0 ? <EmptyState className="m-4" title="No audit events match" message="Change the action filter to widen the search." /> : null}{logs.data?.items.length ? <><DataTable columns={columns} data={logs.data.items} getRowId={(row) => row.id} label="Audit log" /><Pagination page={page} pages={logs.data.page.pages} total={logs.data.page.total} onPage={setPage} /></> : null}
    </Panel></div></AdminShell>;
}
