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
import type { AttendanceBenefitQuote, MembershipPlan, PayOSCreateResponse } from "@/types/api";
import type { GymLocation, MemberDashboardPayload } from "@/types/operations";

export function BuyMembershipPage() {
  const { planId } = useParams();
  const { token } = useAuth();
  const [chosenGymId, setChosenGymId] = useState("");
  const plans = useQuery({ queryKey: ["membership-plans"], queryFn: ({ signal }) => apiRequest<MembershipPlan[]>("/membership-plans", { signal }) });
  const gyms = useQuery({ queryKey: ["gyms", "active"], queryFn: ({ signal }) => apiRequest<GymLocation[]>("/gyms", { signal }) });
  const dashboard = useQuery({ queryKey: ["dashboard", "membership-location"], queryFn: ({ signal }) => apiRequest<MemberDashboardPayload>("/dashboard/me", { token, signal }) });
  const selectedPlan = useMemo(() => plans.data?.find((plan) => plan.id === planId), [planId, plans.data]);
  const gymId = chosenGymId || dashboard.data?.membership?.home_gym_id || "";
  const selectedGym = gyms.data?.find((gym) => gym.id === gymId);
  const benefit = useQuery({
    queryKey: ["attendance-benefit", planId, gymId],
    queryFn: ({ signal }) => apiRequest<AttendanceBenefitQuote>(`/memberships/attendance-benefit/me?plan_id=${planId}&gym_id=${gymId}`, { token, signal }),
    enabled: Boolean(selectedPlan && token && gymId),
  });
  const checkout = useMutation({
    mutationFn: () => apiRequest<PayOSCreateResponse>("/payments/payos/create", {
      method: "POST",
      token,
      body: { membership_plan_id: planId, gym_id: gymId, client_platform: "web" },
    }),
    onSuccess: (result) => {
      sessionStorage.setItem("ypgym:payos:last-transaction", result.transaction_id);
      window.location.assign(result.checkout_url);
    },
  });

  return <MemberShell>
    {plans.isLoading ? <LoadingState title="Loading selected plan" /> : null}
    {plans.isError ? <ErrorState title={toUiError(plans.error).title} message={toUiError(plans.error).message} /> : null}
    {plans.isSuccess && !selectedPlan ? <EmptyState title="Plan unavailable" message="Choose an active plan from the membership plans page." action={<Link className="inline-flex rounded-full bg-primary px-4 py-2 text-sm font-extrabold text-primary-foreground" to="/memberships">View plans</Link>} /> : null}
    {selectedPlan ? <section className="mx-auto max-w-3xl"><p className="page-kicker">Secure checkout</p><h1 className="page-title">Pay with VietQR.</h1><p className="page-description">YPGym calculates the price. payOS presents the VietQR checkout, and your membership activates only after its signed webhook is verified.</p>
      <article className="surface-card mt-8 overflow-hidden"><div className="bg-primary p-6 text-primary-foreground sm:p-8"><p className="text-xs font-extrabold uppercase tracking-[0.13em] text-secondary">Selected membership</p><div className="mt-4 flex flex-wrap items-end justify-between gap-4"><h2 className="font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-none">{selectedPlan.name}</h2><p className="text-xl font-extrabold">{formatMoney(benefit.data?.pricing.final_amount ?? selectedPlan.final_price)}</p></div></div>
        <div className="border-b border-border p-6"><fieldset><legend className="text-sm font-extrabold">{dashboard.data?.membership ? "Keep or change your gym location" : "Choose your gym location"}</legend><p className="mt-1 text-xs text-muted-foreground">Your membership, QR access, attendance, classes, and branch messages use this location.</p>{gyms.isLoading ? <LoadingState className="mt-4" title="Loading gym locations" /> : null}{gyms.isError ? <ErrorState className="mt-4" title="Gym locations unavailable" message={toUiError(gyms.error).message} action={<Button variant="outline" onClick={() => gyms.refetch()}>Retry</Button>} /> : null}<div className="mt-4 grid gap-3 sm:grid-cols-2">{gyms.data?.map((gym) => <label className={`cursor-pointer rounded-2xl border p-4 transition ${gym.id === gymId ? "border-primary bg-primary/5" : "border-border bg-card"}`} key={gym.id}><span className="flex items-start gap-3"><input className="mt-1" type="radio" name="gym-location" value={gym.id} checked={gym.id === gymId} onChange={() => setChosenGymId(gym.id)} /><span><strong className="block">{gym.name}</strong><span className="mt-1 block text-xs text-muted-foreground">{gym.district} · capacity {gym.capacity}</span>{dashboard.data?.membership?.home_gym_id === gym.id ? <span className="mt-2 block text-[10px] font-extrabold uppercase tracking-wider text-primary">Current location</span> : null}</span></span></label>)}</div>{selectedGym ? <p className="mt-3 text-xs font-semibold text-primary">Selected: {selectedGym.name}</p> : <p className="mt-3 text-xs text-destructive">Select a gym before checkout.</p>}</fieldset></div>
        {benefit.isLoading ? <LoadingState className="m-6" title="Checking attendance benefit" /> : null}
        {benefit.isError ? <ErrorState className="m-6" title="Price unavailable" message={toUiError(benefit.error).message} action={<Button variant="outline" onClick={() => benefit.refetch()}>Retry price check</Button>} /> : null}
        {benefit.data ? <><div className="grid gap-4 p-6 sm:grid-cols-2 lg:grid-cols-4"><Detail label="Duration" value={`${selectedPlan.duration_days} days`} /><Detail label="Visits last month" value={`${benefit.data.attended_days}/${benefit.data.period_days} · ${benefit.data.attendance_percentage}%`} /><Detail label="Applied discount" value={`${Number(benefit.data.pricing.applied_discount_percent)}%`} /><Detail label="Final amount" value={formatMoney(benefit.data.pricing.final_amount)} /></div><div className="mx-6 mb-6 rounded-xl border border-primary/25 bg-primary/5 p-4 text-sm"><p className="font-extrabold">{benefitMessage(benefit.data)}</p><p className="mt-1 text-xs text-muted-foreground">The 10% attendance benefit uses distinct QR check-in days from {benefit.data.period_start} through {benefit.data.period_end}. The higher plan or attendance discount applies, and a qualifying month is consumed after one successful renewal.</p></div></> : null}
        <div className="border-t border-border p-6"><fieldset><legend className="text-sm font-extrabold">Payment method</legend><label className="mt-3 flex items-center gap-3 rounded-2xl border border-primary bg-primary/5 p-4"><input type="radio" checked readOnly name="payment-method" /><CreditCard className="size-5 text-primary" aria-hidden /><span><strong>payOS VietQR</strong><span className="block text-xs text-muted-foreground">Napas 24/7 bank transfer to YPGym</span></span></label></fieldset>
          <p className="mt-5 flex items-start gap-2 rounded-xl bg-muted p-4 text-xs leading-5 text-muted-foreground"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />Returning from payOS does not activate the plan by itself. YPGym waits for the signed server webhook.</p>
          {checkout.isError ? <ErrorState className="mt-4" title={toUiError(checkout.error).title} message={toUiError(checkout.error).message} /> : null}
          <Button className="mt-5 w-full rounded-full sm:w-auto" disabled={checkout.isPending || !gymId || !benefit.data || benefit.data.status === "pending"} onClick={() => checkout.mutate()}><CreditCard className="size-4" aria-hidden />{checkout.isPending ? "Preparing VietQR checkout..." : "Continue to payOS"}</Button>
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
