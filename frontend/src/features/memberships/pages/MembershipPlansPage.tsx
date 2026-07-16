import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Check, CreditCard, ShieldAlert, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatMoney } from "@/lib/format";
import type { MembershipPlan } from "@/types/api";

export function MembershipPlansPage() {
  const { user } = useAuth();
  const plans = useQuery({
    queryKey: ["membership-plans"],
    queryFn: ({ signal }) => apiRequest<MembershipPlan[]>("/membership-plans", { signal }),
  });

  return (
    <AppFrame>
      <main id="main-content" className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-16">
        <section className="rounded-[1.5rem] bg-primary px-6 py-9 text-primary-foreground sm:px-9 lg:flex lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <span className="eyebrow-chip"><Sparkles className="size-3.5" aria-hidden /> API-configured plans</span>
            <h1 className="mt-5 font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-[0.84] sm:text-6xl">Membership that keeps up with you.</h1>
            <p className="mt-5 text-sm leading-7 text-primary-foreground/75">Plan names, benefits, discount and final pricing come directly from YPGym. Nothing on this screen is copied from a static design value.</p>
          </div>
          {user ? <Link className="mt-6 inline-flex items-center gap-2 rounded-full border border-primary-foreground/25 px-4 py-2.5 text-sm font-extrabold transition hover:bg-primary-foreground/10 lg:mt-0" to="/app/billing">Billing history <ArrowRight className="size-4" aria-hidden /></Link> : null}
        </section>

        <div className="mt-10 flex items-end justify-between gap-4">
          <div><p className="page-kicker">Choose your plan</p><h2 className="mt-1 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">Available memberships</h2></div>
          {plans.data ? <p className="text-xs font-extrabold uppercase tracking-widest text-muted-foreground">{plans.data.length} active plans</p> : null}
        </div>

        {plans.isLoading ? <LoadingState className="mt-6" title="Loading membership plans" /> : null}
        {plans.isError ? <ErrorState className="mt-6" title={toUiError(plans.error).title} message={toUiError(plans.error).message} /> : null}
        {plans.isSuccess && plans.data.length === 0 ? <EmptyState className="mt-6" title="No active plans" message="Seed membership plans before testing purchase and renewal." /> : null}
        {plans.isSuccess && plans.data.length > 0 ? <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {plans.data.map((plan, index) => <PlanCard key={plan.id} plan={plan} index={index} user={user} />)}
        </section> : null}
      </main>
    </AppFrame>
  );
}

function PlanCard({ plan, index, user }: { plan: MembershipPlan; index: number; user: ReturnType<typeof useAuth>["user"] }) {
  const featured = index === 2;
  return (
    <article className={`relative flex min-h-[27rem] flex-col overflow-hidden rounded-[1.3rem] border p-6 shadow-[0_1.5rem_3.5rem_-3rem_hsl(var(--foreground)/0.45)] ${featured ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card"}`}>
      {featured ? <span className="absolute right-5 top-5 rounded-full bg-secondary px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider text-foreground">Popular rhythm</span> : null}
      <p className={`text-xs font-extrabold uppercase tracking-[0.13em] ${featured ? "text-secondary" : "text-muted-foreground"}`}>0{index + 1} / {plan.duration_days} days</p>
      <h3 className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">{plan.name}</h3>
      <p className={`mt-2 text-xs ${featured ? "text-primary-foreground/65" : "text-muted-foreground"}`}>{plan.tier_availability ?? "All"} member tier{plan.tier_availability ? " availability" : ""}</p>
      <div className="mt-7 border-y border-current/10 py-5"><p className={`text-xs font-bold uppercase tracking-[0.12em] ${featured ? "text-primary-foreground/65" : "text-muted-foreground"}`}>Total investment</p><p className="mt-2 text-3xl font-extrabold">{formatMoney(plan.final_price)}</p>{Number(plan.discount_percent) > 0 ? <p className={`mt-1 text-xs ${featured ? "text-secondary" : "text-accent"}`}>Save {Number(plan.discount_percent)}% from {formatMoney(plan.base_price)}</p> : null}</div>
      <ul className="mt-5 flex-1 space-y-2.5 text-sm">{plan.benefits.map((benefit) => <li className="flex gap-2" key={benefit}><Check className={`mt-0.5 size-4 shrink-0 ${featured ? "text-secondary" : "text-primary"}`} aria-hidden /><span>{benefit}</span></li>)}</ul>
      <PlanAction plan={plan} user={user} featured={featured} />
    </article>
  );
}

function PlanAction({ plan, user, featured }: { plan: MembershipPlan; user: ReturnType<typeof useAuth>["user"]; featured: boolean }) {
  if (!user) return <div className="mt-6 grid grid-cols-2 gap-2"><Link className={`inline-flex items-center justify-center rounded-full px-3 py-2.5 text-xs font-extrabold ${featured ? "bg-secondary text-foreground" : "bg-primary text-primary-foreground"}`} to="/login">Log in</Link><Link className={`inline-flex items-center justify-center rounded-full border px-3 py-2.5 text-xs font-extrabold ${featured ? "border-primary-foreground/30 text-primary-foreground" : "border-border"}`} to="/register">Register</Link></div>;
  if (!user.is_email_verified) return <p className={`mt-6 flex gap-2 rounded-xl border p-3 text-xs leading-5 ${featured ? "border-secondary/30 bg-secondary/10 text-primary-foreground" : "border-accent/30 bg-accent/10 text-foreground"}`}><ShieldAlert className="size-4 shrink-0" aria-hidden />Verify your email before purchasing a membership.</p>;
  return <Link className={`mt-6 inline-flex items-center justify-center gap-2 rounded-full px-4 py-3 text-sm font-extrabold ${featured ? "bg-secondary text-foreground" : "bg-primary text-primary-foreground"}`} to={`/memberships/buy/${plan.id}`}><CreditCard className="size-4" aria-hidden /> Buy or renew <ArrowRight className="size-4" aria-hidden /></Link>;
}
