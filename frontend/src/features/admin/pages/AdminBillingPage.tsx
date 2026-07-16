import { useQuery } from "@tanstack/react-query";
import { CreditCard, Search } from "lucide-react";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime, formatMoney } from "@/lib/format";

type AdminBillingItem = { payment_id: string; user_id: string; member_name: string; member_email: string; plan_name: string; amount: string; status: string; created_at: string };

export function AdminBillingPage() {
  const { token } = useAuth();
  const billing = useQuery({ queryKey: ["admin", "billing"], queryFn: ({ signal }) => apiRequest<AdminBillingItem[]>("/billing/admin/payments", { token, signal }) });
  return <AdminShell>
    <div className="mx-auto max-w-6xl"><div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="page-kicker">Admin billing</p><h1 className="page-title">Payment ledger.</h1><p className="page-description">A role-protected view of the live Day 20 billing endpoint. No CRM data is added locally to fill gaps.</p></div><span className="inline-flex items-center gap-2 rounded-full bg-secondary px-3 py-2 text-xs font-extrabold text-foreground"><CreditCard className="size-4" aria-hidden /> Read-only current release</span></div>
      {billing.isLoading ? <LoadingState className="mt-7" title="Loading admin billing" /> : null}
      {billing.isError ? <ErrorState className="mt-7" title={toUiError(billing.error).title} message={toUiError(billing.error).message} /> : null}
      {billing.isSuccess && billing.data.length === 0 ? <EmptyState className="mt-7" title="No payments yet" message="Member mock purchases will appear in this backend-backed table." /> : null}
      {billing.isSuccess && billing.data.length > 0 ? <section className="surface-card mt-8 overflow-hidden"><div className="flex items-center justify-between border-b border-border bg-card px-5 py-4"><div><h2 className="font-['Barlow_Condensed'] text-3xl font-bold uppercase leading-none">Recent transactions</h2><p className="mt-1 text-xs text-muted-foreground">Horizontal scrolling is retained on narrow screens so the data stays readable.</p></div><Search className="size-5 text-muted-foreground" aria-hidden /></div><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-muted/70 text-[10px] font-extrabold uppercase tracking-[0.12em] text-muted-foreground"><tr><th className="px-5 py-4">Member</th><th className="px-5 py-4">Plan</th><th className="px-5 py-4">Amount</th><th className="px-5 py-4">Status</th><th className="px-5 py-4">Created</th></tr></thead><tbody>{billing.data.map((item) => <tr className="border-t border-border transition hover:bg-muted/45" key={item.payment_id}><td className="px-5 py-4"><p className="font-bold">{item.member_name}</p><p className="mt-1 text-xs text-muted-foreground">{item.member_email}</p></td><td className="px-5 py-4 font-semibold">{item.plan_name}</td><td className="px-5 py-4 font-['Barlow_Condensed'] text-xl font-bold uppercase">{formatMoney(item.amount)}</td><td className="px-5 py-4"><span className="rounded-full bg-secondary/25 px-2.5 py-1 text-[10px] font-extrabold uppercase text-foreground">{item.status}</span></td><td className="px-5 py-4 text-xs text-muted-foreground">{formatDateTime(item.created_at)}</td></tr>)}</tbody></table></div></section> : null}
    </div>
  </AdminShell>;
}
