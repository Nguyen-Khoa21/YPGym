import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, ReceiptText, Search, WalletCards } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { DataTable } from "@/components/operations/DataTable";
import { MetricCard, OperationsHeader, Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest, downloadApiFile } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime, formatMoney } from "@/lib/format";
import type { BillingInvoice, BillingPage, BillingPayment } from "@/types/operations";

const paymentColumns: ColumnDef<BillingPayment>[] = [
  { header: "Member", cell: ({ row }) => <div><strong>{row.original.member_name}</strong><p className="mt-1 text-[11px] text-muted-foreground">{row.original.member_email}</p></div> },
  { header: "Plan", accessorKey: "plan_name" },
  { header: "Tier", cell: ({ row }) => <span className="capitalize">{row.original.member_tier}</span> },
  { header: "Amount", cell: ({ row }) => <strong>{formatMoney(row.original.amount)}</strong> },
  { header: "Status", cell: ({ row }) => <StatusBadge value={row.original.status} /> },
  { header: "Created", cell: ({ row }) => formatDateTime(row.original.created_at) },
];

const invoiceColumns: ColumnDef<BillingInvoice>[] = [
  { header: "Invoice", cell: ({ row }) => <strong>{row.original.invoice_number}</strong> },
  { header: "Member", cell: ({ row }) => <div><strong>{row.original.member_name}</strong><p className="mt-1 text-[11px] text-muted-foreground">{row.original.member_email}</p></div> },
  { header: "Plan", accessorKey: "plan_name" },
  { header: "Amount", cell: ({ row }) => <strong>{formatMoney(row.original.amount)}</strong> },
  { header: "Transaction", cell: ({ row }) => formatDateTime(row.original.transaction_date) },
];

export function AdminBillingPage() {
  const { token } = useAuth();
  const [tab, setTab] = useState<"payments" | "invoices">("payments");
  const [member, setMember] = useState("");
  const [appliedMember, setAppliedMember] = useState("");
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [plan, setPlan] = useState("");
  const [tier, setTier] = useState("");
  const [page, setPage] = useState(1);
  const query = new URLSearchParams({ page: String(page), page_size: "20" });
  if (appliedMember) query.set("member", appliedMember);
  if (status) query.set("status", status);
  if (dateFrom) query.set("date_from", `${dateFrom}T00:00:00Z`);
  if (dateTo) query.set("date_to", `${dateTo}T23:59:59Z`);
  if (plan) query.set("plan", plan);
  if (tier) query.set("tier", tier);
  const billing = useQuery({
    queryKey: ["admin", "billing", tab, query.toString()],
    queryFn: ({ signal }) => apiRequest<BillingPage<BillingPayment> | BillingPage<BillingInvoice>>(`/admin/billing/${tab}?${query}`, { token, signal }),
  });

  async function exportCsv() {
    try {
      const exportQuery = new URLSearchParams(query); exportQuery.delete("page"); exportQuery.delete("page_size");
      const blob = await downloadApiFile(`/admin/billing/${tab}/export.csv?${exportQuery}`, token);
      const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `ypgym-${tab}.csv`; anchor.click(); URL.revokeObjectURL(url);
      toast.success(`${tab === "payments" ? "Payment" : "Invoice"} export downloaded`);
    } catch (error) { toast.error(toUiError(error).message); }
  }

  const data = billing.data;
  return <AdminShell><div className="mx-auto max-w-7xl">
    <OperationsHeader kicker="Admin billing" title="Money, traceable." description="Filtered payments and invoices share the exact same server-side semantics as their audited CSV exports." actions={<Button variant="outline" onClick={exportCsv}><Download className="size-4" /> Export {tab}</Button>} />
    {data ? <div className="ops-metrics"><MetricCard label={`${tab} found`} value={data.page.total} /><MetricCard label="Filtered total" value={formatMoney(data.total_amount)} tone="forest" /><MetricCard label="Current page" value={`${data.page.page}/${Math.max(data.page.pages, 1)}`} tone="lime" /><MetricCard label="Access" value="Admin" detail="Sensitive billing scope" tone="coral" /></div> : null}
    <Panel title="Billing ledger" detail="Staff and manager roles are intentionally excluded from this sensitive dataset." actions={<div className="ops-filter-row"><Button variant={tab === "payments" ? "secondary" : "ghost"} onClick={() => { setTab("payments"); setPage(1); }}><WalletCards className="size-4" /> Payments</Button><Button variant={tab === "invoices" ? "secondary" : "ghost"} onClick={() => { setTab("invoices"); setPage(1); }}><ReceiptText className="size-4" /> Invoices</Button></div>}>
      <form className="ops-toolbar" onSubmit={(event) => { event.preventDefault(); setAppliedMember(member); setPage(1); }}>
        <Search className="size-4 text-muted-foreground" />
        <input aria-label="Search billing member" placeholder="Member name or email" value={member} onChange={(event) => setMember(event.target.value)} />
        <select aria-label="Filter billing status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">All statuses</option><option value="succeeded">Succeeded</option><option value="failed">Failed</option></select>
        <input aria-label="Filter billing plan" placeholder="Plan" value={plan} onChange={(event) => { setPlan(event.target.value); setPage(1); }} />
        <select aria-label="Filter billing tier" value={tier} onChange={(event) => { setTier(event.target.value); setPage(1); }}><option value="">All tiers</option><option value="normal">Normal</option><option value="advance">Advance</option><option value="vip">VIP</option></select>
        <input aria-label="Billing date from" type="date" value={dateFrom} onChange={(event) => { setDateFrom(event.target.value); setPage(1); }} />
        <input aria-label="Billing date to" type="date" value={dateTo} onChange={(event) => { setDateTo(event.target.value); setPage(1); }} />
        <Button type="submit" variant="secondary">Apply</Button>
      </form>
      {billing.isLoading ? <LoadingState className="m-4" title={`Loading ${tab}`} /> : null}
      {billing.isError ? <ErrorState className="m-4" title={toUiError(billing.error).title} message={toUiError(billing.error).message} action={<Button variant="outline" onClick={() => billing.refetch()}>Retry</Button>} /> : null}
      {data?.items.length === 0 ? <EmptyState className="m-4" title={`No ${tab} match`} message="Adjust the current billing filters." /> : null}
      {data?.items.length ? <>{tab === "payments" ? <DataTable columns={paymentColumns} data={data.items as BillingPayment[]} getRowId={(row) => row.payment_id} label="Filtered payments" /> : <DataTable columns={invoiceColumns} data={data.items as BillingInvoice[]} getRowId={(row) => row.invoice_id} label="Filtered invoices" />}<Pagination page={page} pages={data.page.pages} total={data.page.total} onPage={setPage} /></> : null}
    </Panel>
  </div></AdminShell>;
}
