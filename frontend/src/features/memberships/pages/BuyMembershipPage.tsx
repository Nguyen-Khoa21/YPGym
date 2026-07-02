import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, CreditCard } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { Button, ButtonLink } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDate, formatMoney } from "@/lib/format";
import type { MembershipPlan, PurchaseResponse } from "@/types/api";

export function BuyMembershipPage() {
  const { planId } = useParams();
  const { token } = useAuth();
  const [confirmed, setConfirmed] = useState(false);
  const [idempotencyKey] = useState(() =>
    window.crypto?.randomUUID?.() ?? `purchase-${Date.now()}`,
  );

  const plans = useQuery({
    queryKey: ["membership-plans"],
    queryFn: () => apiRequest<MembershipPlan[]>("/membership-plans"),
  });

  const selectedPlan = useMemo(
    () => plans.data?.find((plan) => plan.id === planId),
    [planId, plans.data],
  );

  const purchase = useMutation({
    mutationFn: () =>
      apiRequest<PurchaseResponse>("/memberships/purchase", {
        method: "POST",
        token,
        body: {
          plan_id: planId,
          idempotency_key: idempotencyKey,
          mock_payment_confirmed: confirmed,
        },
      }),
  });

  return (
    <AppFrame>
      <main className="mx-auto max-w-4xl px-5 py-10">
        {plans.isLoading ? <LoadingState title="Loading selected plan" /> : null}

        {plans.isError ? (
          <ErrorState
            title={toUiError(plans.error).title}
            message={toUiError(plans.error).message}
          />
        ) : null}

        {plans.isSuccess && !selectedPlan ? (
          <EmptyState
            title="Plan unavailable"
            message="Choose an active plan from the membership plans page."
            action={
              <ButtonLink asChild>
                <Link to="/memberships">View plans</Link>
              </ButtonLink>
            }
          />
        ) : null}

        {selectedPlan && !purchase.data ? (
          <section className="rounded-lg border border-border bg-card p-6 shadow-sm">
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-primary">
                  Mock payment
                </p>
                <h1 className="mt-2 text-3xl font-bold">Buy/Renew Membership</h1>
                <p className="mt-2 text-muted-foreground">
                  Price is calculated by the backend from the selected plan.
                </p>
              </div>
              <span className="rounded-md bg-muted px-3 py-2 text-sm font-semibold">
                {selectedPlan.duration_days} days
              </span>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">Plan</p>
                <p className="mt-1 text-lg font-bold">{selectedPlan.name}</p>
              </div>
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">Discount</p>
                <p className="mt-1 text-lg font-bold">
                  {Number(selectedPlan.discount_percent)}%
                </p>
              </div>
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">Amount due</p>
                <p className="mt-1 text-lg font-bold">
                  {formatMoney(selectedPlan.final_price)}
                </p>
              </div>
            </div>

            {purchase.isError ? (
              <ErrorState
                className="mt-5"
                title={toUiError(purchase.error).title}
                message={toUiError(purchase.error).message}
              />
            ) : null}

            <label className="mt-6 flex cursor-pointer items-start gap-3 rounded-lg border border-border bg-muted/40 p-4 text-sm">
              <input
                className="mt-1 size-4"
                type="checkbox"
                checked={confirmed}
                onChange={(event) => setConfirmed(event.target.checked)}
              />
              <span>
                I confirm this mock payment should create or renew my YPGym
                membership and generate an invoice.
              </span>
            </label>

            <Button
              className="mt-6 w-full sm:w-auto"
              disabled={!confirmed || purchase.isPending}
              onClick={() => purchase.mutate()}
            >
              <CreditCard className="size-4" aria-hidden />
              {purchase.isPending ? "Processing..." : "Confirm mock payment"}
            </Button>
          </section>
        ) : null}

        {purchase.data ? (
          <section className="rounded-lg border border-secondary/30 bg-card p-6 shadow-sm">
            <CheckCircle2 className="size-9 text-secondary" aria-hidden />
            <h1 className="mt-4 text-3xl font-bold">Membership active</h1>
            <p className="mt-2 text-muted-foreground">{purchase.data.message}</p>
            <div className="mt-5 grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">Plan</p>
                <p className="mt-1 font-bold">{purchase.data.membership.plan_name}</p>
              </div>
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">Expires</p>
                <p className="mt-1 font-bold">
                  {formatDate(purchase.data.membership.expiry_date)}
                </p>
              </div>
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">Paid</p>
                <p className="mt-1 font-bold">{formatMoney(purchase.data.payment.amount)}</p>
              </div>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <ButtonLink asChild>
                <Link to="/billing">View invoice history</Link>
              </ButtonLink>
              <ButtonLink asChild variant="outline">
                <Link to="/member">Member dashboard</Link>
              </ButtonLink>
            </div>
          </section>
        ) : null}
      </main>
    </AppFrame>
  );
}
