import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, CreditCard, ReceiptText } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDate, formatMoney } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { MembershipPlan, PurchaseResponse } from "@/types/api";

export function BuyMembershipPage() {
  const { planId } = useParams();
  const { token } = useAuth();
  const [confirmed, setConfirmed] = useState(false);
  const [idempotencyKey] = useState(() => window.crypto?.randomUUID?.() ?? `purchase-${Date.now()}`);
  const plans = useQuery({ queryKey: ["membership-plans"], queryFn: ({ signal }) => apiRequest<MembershipPlan[]>("/membership-plans", { signal }) });
  const selectedPlan = useMemo(() => plans.data?.find((plan) => plan.id === planId), [planId, plans.data]);
  const purchase = useMutation({
    mutationFn: () => apiRequest<PurchaseResponse>("/memberships/purchase", { method: "POST", token, body: { plan_id: planId, idempotency_key: idempotencyKey, mock_payment_confirmed: confirmed } }),
    onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["billing"] }), queryClient.invalidateQueries({ queryKey: ["dashboard"] })]); },
  });

  return <MemberShell>
    {plans.isLoading ? <LoadingState title="Loading selected plan" /> : null}
    {plans.isError ? <ErrorState title={toUiError(plans.error).title} message={toUiError(plans.error).message} /> : null}
    {plans.isSuccess && !selectedPlan ? <EmptyState title="Plan unavailable" message="Choose an active plan from the membership plans page." action={<Link className="inline-flex rounded-full bg-primary px-4 py-2 text-sm font-extrabold text-primary-foreground" to="/memberships">View plans</Link>} /> : null}
    {selectedPlan && !purchase.data ? <PurchaseReview plan={selectedPlan} confirmed={confirmed} setConfirmed={setConfirmed} pending={purchase.isPending} onConfirm={() => purchase.mutate()} error={purchase.isError ? toUiError(purchase.error) : null} /> : null}
    {purchase.data ? <PurchaseSuccess result={purchase.data} /> : null}
  </MemberShell>;
}

function PurchaseReview({ plan, confirmed, setConfirmed, pending, onConfirm, error }: { plan: MembershipPlan; confirmed: boolean; setConfirmed: (value: boolean) => void; pending: boolean; onConfirm: () => void; error: ReturnType<typeof toUiError> | null }) {
  return <section className="mx-auto max-w-3xl"><p className="page-kicker">Review & confirm</p><h1 className="page-title">One last check.</h1><p className="page-description">This uses the live membership purchase endpoint. The backend recalculates the price and keeps this request idempotent if the button is retried.</p><article className="surface-card mt-8 overflow-hidden"><div className="bg-primary p-6 text-primary-foreground sm:p-8"><p className="text-xs font-extrabold uppercase tracking-[0.13em] text-secondary">Selected membership</p><div className="mt-4 flex flex-wrap items-end justify-between gap-4"><h2 className="font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-none">{plan.name}</h2><p className="text-xl font-extrabold">{formatMoney(plan.final_price)}</p></div></div><div className="grid gap-4 p-6 sm:grid-cols-3"><Detail label="Duration" value={`${plan.duration_days} days`} /><Detail label="Configured discount" value={`${Number(plan.discount_percent)}%`} /><Detail label="Final amount" value={formatMoney(plan.final_price)} /></div><div className="border-t border-border p-6"><label className="flex cursor-pointer items-start gap-3 rounded-2xl bg-muted/70 p-4 text-sm leading-6"><input className="mt-1 size-4 accent-primary" type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /><span>I understand this mock payment will create or extend my membership and generate an invoice in my billing history.</span></label>{error ? <ErrorState className="mt-4" title={error.title} message={error.message} /> : null}<Button className="mt-5 w-full rounded-full sm:w-auto" disabled={!confirmed || pending} onClick={onConfirm}><CreditCard className="size-4" aria-hidden />{pending ? "Processing secure request..." : "Confirm mock payment"}</Button></div></article></section>;
}

function PurchaseSuccess({ result }: { result: PurchaseResponse }) {
  const isRenewal = result.invoice.membership_start_date !== result.membership.start_date;
  return <section className="mx-auto max-w-3xl"><article className="overflow-hidden rounded-[1.4rem] bg-primary p-7 text-primary-foreground sm:p-10"><span className="grid size-14 place-items-center rounded-2xl bg-secondary text-foreground"><CheckCircle2 className="size-7" aria-hidden /></span><p className="mt-7 text-xs font-extrabold uppercase tracking-[0.14em] text-secondary">{isRenewal ? "Renewal confirmed" : "Purchase confirmed"}</p><h1 className="mt-2 font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-[0.86]">{isRenewal ? "Your membership has been extended." : "Your membership is active."}</h1><p className="mt-5 text-sm leading-7 text-primary-foreground/75">{result.message}</p><div className="mt-8 grid gap-3 sm:grid-cols-3"><Detail dark label="Plan" value={result.membership.plan_name} /><Detail dark label="Expiry" value={formatDate(result.membership.expiry_date)} /><Detail dark label="Payment" value={formatMoney(result.payment.amount)} /></div></article><div className="mt-5 flex flex-wrap gap-3"><Link className="inline-flex items-center gap-2 rounded-full bg-secondary px-5 py-3 text-sm font-extrabold text-foreground" to="/app/billing"><ReceiptText className="size-4" aria-hidden /> View invoice history</Link><Link className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-5 py-3 text-sm font-extrabold" to="/app/dashboard">Member dashboard <ArrowRight className="size-4" aria-hidden /></Link></div></section>;
}

function Detail({ label, value, dark = false }: { label: string; value: string; dark?: boolean }) { return <div className={`rounded-xl border p-4 ${dark ? "border-primary-foreground/15 bg-primary-foreground/10" : "border-border bg-card"}`}><p className={`text-[10px] font-extrabold uppercase tracking-[0.12em] ${dark ? "text-primary-foreground/60" : "text-muted-foreground"}`}>{label}</p><p className="mt-2 text-sm font-extrabold">{value}</p></div>; }
