import { useMutation, useQuery } from "@tanstack/react-query";
import { CreditCard, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatMoney } from "@/lib/format";
import type { AttendanceBenefitQuote, MembershipPlan, VNPayCreateResponse } from "@/types/api";

export function BuyMembershipPage() {
  const { planId } = useParams();
  const { token } = useAuth();
  const [bankCode, setBankCode] = useState("");
  const [locale, setLocale] = useState<"vn" | "en">("vn");
  const plans = useQuery({ queryKey: ["membership-plans"], queryFn: ({ signal }) => apiRequest<MembershipPlan[]>("/membership-plans", { signal }) });
  const selectedPlan = useMemo(() => plans.data?.find((plan) => plan.id === planId), [planId, plans.data]);
  const benefit = useQuery({
    queryKey: ["attendance-benefit", planId],
    queryFn: ({ signal }) => apiRequest<AttendanceBenefitQuote>(`/memberships/attendance-benefit/me?plan_id=${planId}`, { token, signal }),
    enabled: Boolean(selectedPlan && token),
  });
  const checkout = useMutation({
    mutationFn: () => apiRequest<VNPayCreateResponse>("/payments/vnpay/create", {
      method: "POST",
      token,
      body: { membership_plan_id: planId, locale, bank_code: bankCode || null, client_platform: "web" },
    }),
    onSuccess: (result) => {
      sessionStorage.setItem("ypgym:vnpay:last-transaction", result.transaction_id);
      window.location.assign(result.payment_url);
    },
  });

  return <MemberShell>
    {plans.isLoading ? <LoadingState title="Loading selected plan" /> : null}
    {plans.isError ? <ErrorState title={toUiError(plans.error).title} message={toUiError(plans.error).message} /> : null}
    {plans.isSuccess && !selectedPlan ? <EmptyState title="Plan unavailable" message="Choose an active plan from the membership plans page." action={<Link className="inline-flex rounded-full bg-primary px-4 py-2 text-sm font-extrabold text-primary-foreground" to="/memberships">View plans</Link>} /> : null}
    {selectedPlan ? <section className="mx-auto max-w-3xl"><p className="page-kicker">Secure checkout</p><h1 className="page-title">Pay with VNPay.</h1><p className="page-description">YPGym calculates the price. VNPay collects the payment, and your membership activates only after VNPay confirms it directly to YPGym.</p>
      <article className="surface-card mt-8 overflow-hidden"><div className="bg-primary p-6 text-primary-foreground sm:p-8"><p className="text-xs font-extrabold uppercase tracking-[0.13em] text-secondary">Selected membership</p><div className="mt-4 flex flex-wrap items-end justify-between gap-4"><h2 className="font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-none">{selectedPlan.name}</h2><p className="text-xl font-extrabold">{formatMoney(benefit.data?.pricing.final_amount ?? selectedPlan.final_price)}</p></div></div>
        {benefit.isLoading ? <LoadingState className="m-6" title="Checking attendance benefit" /> : null}
        {benefit.isError ? <ErrorState className="m-6" title="Price unavailable" message={toUiError(benefit.error).message} action={<Button variant="outline" onClick={() => benefit.refetch()}>Retry price check</Button>} /> : null}
        {benefit.data ? <><div className="grid gap-4 p-6 sm:grid-cols-2 lg:grid-cols-4"><Detail label="Duration" value={`${selectedPlan.duration_days} days`} /><Detail label="Visits last month" value={`${benefit.data.attended_days}/${benefit.data.period_days} · ${benefit.data.attendance_percentage}%`} /><Detail label="Applied discount" value={`${Number(benefit.data.pricing.applied_discount_percent)}%`} /><Detail label="Final amount" value={formatMoney(benefit.data.pricing.final_amount)} /></div><div className="mx-6 mb-6 rounded-xl border border-primary/25 bg-primary/5 p-4 text-sm"><p className="font-extrabold">{benefitMessage(benefit.data)}</p><p className="mt-1 text-xs text-muted-foreground">The 10% attendance benefit uses distinct QR check-in days from {benefit.data.period_start} through {benefit.data.period_end}. The higher plan or attendance discount applies, and a qualifying month is consumed after one successful renewal.</p></div></> : null}
        <div className="border-t border-border p-6"><fieldset><legend className="text-sm font-extrabold">Payment method</legend><label className="mt-3 flex items-center gap-3 rounded-2xl border border-primary bg-primary/5 p-4"><input type="radio" checked readOnly name="payment-method" /><CreditCard className="size-5 text-primary" aria-hidden /><span><strong>VNPay</strong><span className="block text-xs text-muted-foreground">Secure sandbox bank, card or QR checkout</span></span></label></fieldset>
          <div className="mt-5 grid gap-4 sm:grid-cols-2"><label className="grid gap-2 text-sm font-bold">Payment option<select className="rounded-xl border border-border bg-card px-3 py-3 font-normal" value={bankCode} onChange={(event) => setBankCode(event.target.value)}><option value="">Choose at VNPay</option><option value="VNPAYQR">VNPay QR</option><option value="VNBANK">Vietnam bank account/card</option><option value="INTCARD">International card</option></select></label><label className="grid gap-2 text-sm font-bold">VNPay language<select className="rounded-xl border border-border bg-card px-3 py-3 font-normal" value={locale} onChange={(event) => setLocale(event.target.value as "vn" | "en")}><option value="vn">Vietnamese</option><option value="en">English</option></select></label></div>
          <p className="mt-5 flex items-start gap-2 rounded-xl bg-muted p-4 text-xs leading-5 text-muted-foreground"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />Returning from VNPay does not activate the plan by itself. This page waits for the signed VNPay server notification.</p>
          {checkout.isError ? <ErrorState className="mt-4" title={toUiError(checkout.error).title} message={toUiError(checkout.error).message} /> : null}
          <Button className="mt-5 w-full rounded-full sm:w-auto" disabled={checkout.isPending || !benefit.data || benefit.data.status === "pending"} onClick={() => checkout.mutate()}><CreditCard className="size-4" aria-hidden />{checkout.isPending ? "Preparing VNPay checkout..." : "Continue to VNPay"}</Button>
        </div></article></section> : null}
  </MemberShell>;
}

function Detail({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-border bg-card p-4"><p className="text-[10px] font-extrabold uppercase tracking-[0.12em] text-muted-foreground">{label}</p><p className="mt-2 text-sm font-extrabold">{value}</p></div>; }

function benefitMessage(value: AttendanceBenefitQuote) {
  if (value.status === "eligible") return value.pricing.attendance_benefit_selected ? "Attendance benefit selected under the better-of rule." : "Your plan discount is higher, so it applies under the better-of rule.";
  if (value.status === "pending") return "An attendance-discounted renewal is already pending.";
  if (value.status === "consumed") return "This attendance month has already been used for a successful renewal.";
  if (value.status === "not_renewal") return "Attendance benefits apply to active membership renewals, not first purchases.";
  return `Attendance benefit requires ${Number(value.threshold_percentage)}% of the previous calendar month's days.`;
}
