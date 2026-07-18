import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, Search, UserRoundPlus } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { DataTable } from "@/components/operations/DataTable";
import { MetricCard, OperationsHeader, Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest, downloadApiFile } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDate } from "@/lib/format";
import type { AdminMember, AdminMemberPage } from "@/types/operations";

const columns: ColumnDef<AdminMember>[] = [
  { header: "Member", cell: ({ row }) => <div><Link className="font-extrabold text-primary underline-offset-4 hover:underline" to={`/admin/members/${row.original.id}`}>{row.original.name}</Link><p className="mt-1 text-[11px] text-muted-foreground">{row.original.email}</p></div> },
  { header: "Contact", cell: ({ row }) => <span>{row.original.phone}</span> },
  { header: "Role / tier", cell: ({ row }) => <div className="capitalize"><strong>{row.original.role}</strong><p className="mt-1 text-[11px] text-muted-foreground">{row.original.tier}</p></div> },
  { header: "Membership", cell: ({ row }) => row.original.membership ? <div><StatusBadge value={row.original.membership.status} /><p className="mt-1.5 text-[11px] text-muted-foreground">{row.original.membership.plan_name}</p></div> : <StatusBadge value="none" /> },
  { header: "Expiry", cell: ({ row }) => row.original.membership ? formatDate(row.original.membership.expiry_date) : "-" },
  { header: "Verified", cell: ({ row }) => <StatusBadge value={row.original.is_email_verified ? "verified" : "pending"} /> },
];

export function AdminMembersPage() {
  const { token } = useAuth();
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("search") ?? "");
  const page = Number(params.get("page") ?? "1");
  const queryString = params.toString();
  const members = useQuery({
    queryKey: ["admin", "members", queryString],
    queryFn: ({ signal }) => apiRequest<AdminMemberPage>(`/admin/members?${queryString || "page=1"}`, { token, signal }),
  });

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.set("page", "1");
    setParams(next);
  }

  async function exportCsv() {
    try {
      const exportParams = new URLSearchParams(params);
      exportParams.delete("page");
      const blob = await downloadApiFile(`/admin/members/export.csv?${exportParams}`, token);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = "ypgym-members.csv"; anchor.click(); URL.revokeObjectURL(url);
      toast.success("Member export downloaded");
    } catch (error) { toast.error(toUiError(error).message); }
  }

  return <AdminShell><div className="mx-auto max-w-7xl">
    <OperationsHeader kicker="Member CRM" title="Know every member." description="Search and filter live profiles, membership state and expiry data without exposing account secrets." actions={<Button variant="outline" onClick={exportCsv}><Download className="size-4" /> Export filtered CSV</Button>} />
    {members.data ? <div className="ops-metrics"><MetricCard label="Visible records" value={members.data.summary.total} detail="Current filter set" /><MetricCard label="Active" value={members.data.summary.active} tone="forest" /><MetricCard label="Expiring soon" value={members.data.summary.expiring_soon} tone="lime" /><MetricCard label="Needs attention" value={members.data.summary.expired_or_inactive + members.data.summary.frozen} tone="coral" /></div> : null}
    <Panel title="Member directory" detail="Filters are encoded in the URL and applied by PostgreSQL.">
      <form className="ops-toolbar" onSubmit={(event) => { event.preventDefault(); updateParam("search", search); }}>
        <Search className="size-4 text-muted-foreground" /><input aria-label="Search members" placeholder="Name, email or phone" value={search} onChange={(event) => setSearch(event.target.value)} />
        <select aria-label="Filter role" value={params.get("role") ?? ""} onChange={(event) => updateParam("role", event.target.value)}><option value="">All roles</option><option value="member">Member</option><option value="staff">Staff</option><option value="manager">Manager</option><option value="admin">Admin</option><option value="pt">PT</option></select>
        <select aria-label="Filter tier" value={params.get("tier") ?? ""} onChange={(event) => updateParam("tier", event.target.value)}><option value="">All tiers</option><option value="normal">Normal</option><option value="advance">Advance</option><option value="vip">VIP</option></select>
        <select aria-label="Filter membership status" value={params.get("status") ?? ""} onChange={(event) => updateParam("status", event.target.value)}><option value="">All states</option><option value="active">Active</option><option value="expiring_soon">Expiring soon</option><option value="frozen">Frozen</option><option value="expired">Expired</option><option value="cancelled">Cancelled</option><option value="revoked">Revoked</option></select>
        <input aria-label="Expiry from" type="date" value={params.get("expiry_from") ?? ""} onChange={(event) => updateParam("expiry_from", event.target.value)} />
        <input aria-label="Expiry to" type="date" value={params.get("expiry_to") ?? ""} onChange={(event) => updateParam("expiry_to", event.target.value)} />
        <Button type="submit" variant="secondary">Apply search</Button>
      </form>
      {members.isLoading ? <LoadingState className="m-4" title="Loading member CRM" /> : null}
      {members.isError ? <ErrorState className="m-4" title={toUiError(members.error).title} message={toUiError(members.error).message} action={<Button variant="outline" onClick={() => members.refetch()}>Retry</Button>} /> : null}
      {members.data?.items.length === 0 ? <EmptyState className="m-4" title="No members match" message="Adjust the filters or search term." action={<Button variant="outline" onClick={() => { setSearch(""); setParams({ page: "1" }); }}>Clear filters</Button>} /> : null}
      {members.data?.items.length ? <><DataTable columns={columns} data={members.data.items} getRowId={(row) => row.id} label="Member CRM results" /><Pagination page={page} pages={members.data.page.pages} total={members.data.page.total} onPage={(nextPage) => { const next = new URLSearchParams(params); next.set("page", String(nextPage)); setParams(next); }} /></> : null}
    </Panel>
    <p className="mt-4 flex items-center gap-2 text-xs text-muted-foreground"><UserRoundPlus className="size-4" /> New accounts enter this directory through the real registration and seed flows.</p>
  </div></AdminShell>;
}
