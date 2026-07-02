import { useQuery } from "@tanstack/react-query";
import { Check, CreditCard, ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";

import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { ButtonLink } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatMoney } from "@/lib/format";
import type { MembershipPlan } from "@/types/api";

export function MembershipPlansPage() {
  const { user } = useAuth();
  const plans = useQuery({
    queryKey: ["membership-plans"],
    queryFn: () => apiRequest<MembershipPlan[]>("/membership-plans"),
  });

  return (
    <AppFrame>
      <main className="mx-auto max-w-6xl px-5 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-primary">
              Memberships
            </p>
            <h1 className="mt-2 text-3xl font-bold">Membership Plans</h1>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              Choose a plan duration, confirm mock payment, and receive an
              immutable invoice in your billing history.
            </p>
          </div>
          <ButtonLink asChild variant="outline">
            <Link to="/billing">Payment history</Link>
          </ButtonLink>
        </div>

        {plans.isLoading ? <LoadingState title="Loading membership plans" /> : null}

        {plans.isError ? (
          <ErrorState
            title={toUiError(plans.error).title}
            message={toUiError(plans.error).message}
          />
        ) : null}

        {plans.isSuccess && plans.data.length === 0 ? (
          <EmptyState
            title="No active plans"
            message="Seed membership plans before testing purchase and renewal."
          />
        ) : null}

        {plans.isSuccess && plans.data.length > 0 ? (
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {plans.data.map((plan) => (
              <article
                key={plan.id}
                className="flex min-h-[420px] flex-col rounded-lg border border-border bg-card p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-bold">{plan.name}</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {plan.duration_days} days · {plan.tier_availability ?? "all"} tier
                    </p>
                  </div>
                  {Number(plan.discount_percent) > 0 ? (
                    <span className="rounded-md bg-accent/15 px-2 py-1 text-xs font-bold text-accent-foreground">
                      {Number(plan.discount_percent)}% off
                    </span>
                  ) : null}
                </div>

                <div className="mt-6">
                  <p className="text-sm text-muted-foreground">Final price</p>
                  <p className="text-3xl font-bold">{formatMoney(plan.final_price)}</p>
                  {Number(plan.discount_percent) > 0 ? (
                    <p className="mt-1 text-sm text-muted-foreground">
                      Base {formatMoney(plan.base_price)}
                    </p>
                  ) : null}
                </div>

                <ul className="mt-6 flex-1 space-y-3 text-sm">
                  {plan.benefits.map((benefit) => (
                    <li key={benefit} className="flex gap-2">
                      <Check className="mt-0.5 size-4 shrink-0 text-secondary" aria-hidden />
                      <span>{benefit}</span>
                    </li>
                  ))}
                </ul>

                <PlanAction plan={plan} user={user} />
              </article>
            ))}
          </section>
        ) : null}
      </main>
    </AppFrame>
  );
}

function PlanAction({
  plan,
  user,
}: {
  plan: MembershipPlan;
  user: ReturnType<typeof useAuth>["user"];
}) {
  if (!user) {
    return (
      <div className="mt-6 grid gap-2 sm:grid-cols-2">
        <ButtonLink asChild>
          <Link to="/login">
            <CreditCard className="size-4" aria-hidden />
            Login
          </Link>
        </ButtonLink>
        <ButtonLink asChild variant="outline">
          <Link to="/register">Register</Link>
        </ButtonLink>
      </div>
    );
  }

  if (!user.is_email_verified) {
    return (
      <div className="mt-6 rounded-lg border border-accent/30 bg-accent/10 p-3 text-sm">
        <ShieldAlert className="mb-2 size-4" aria-hidden />
        Verify your email before buying a membership.
      </div>
    );
  }

  return (
    <ButtonLink asChild className="mt-6">
      <Link to={`/memberships/buy/${plan.id}`}>
        <CreditCard className="size-4" aria-hidden />
        Buy or renew
      </Link>
    </ButtonLink>
  );
}
