import { useQuery } from "@tanstack/react-query";
import { CreditCard, ReceiptText, UserCog } from "lucide-react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { ButtonLink } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDate, formatMoney } from "@/lib/format";
import type { InvoiceHistoryItem, PaymentHistoryItem } from "@/types/api";

export function MemberDashboardPage() {
  const { user, token } = useAuth();
  const payments = useQuery({
    queryKey: ["dashboard", "payments"],
    enabled: Boolean(token),
    queryFn: () =>
      apiRequest<PaymentHistoryItem[]>("/billing/me/payments", { token }),
  });
  const invoices = useQuery({
    queryKey: ["dashboard", "invoices"],
    enabled: Boolean(token),
    queryFn: () =>
      apiRequest<InvoiceHistoryItem[]>("/billing/me/invoices", { token }),
  });
  const latestPayment = payments.data?.[0];
  const latestInvoice = invoices.data?.[0];
  const hasError = payments.error || invoices.error;

  return (
    <AppFrame>
      <main className="mx-auto max-w-6xl px-5 py-10">
        <div className="mb-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-primary">
            Member workspace
          </p>
          <h1 className="mt-2 text-3xl font-bold">Member Dashboard</h1>
          <p className="mt-2 text-muted-foreground">
            Welcome back, {user?.name}. Your membership and billing tools are
            ready for testing.
          </p>
        </div>

        {payments.isLoading || invoices.isLoading ? (
          <LoadingState className="mb-6" title="Loading account summary" />
        ) : null}

        {hasError ? (
          <ErrorState
            className="mb-6"
            title={toUiError(hasError).title}
            message={toUiError(hasError).message}
          />
        ) : null}

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <CreditCard className="size-6 text-secondary" aria-hidden />
            <h2 className="mt-4 text-lg font-semibold">Latest payment</h2>
            <p className="mt-2 text-2xl font-bold">
              {latestPayment ? formatMoney(latestPayment.amount) : "No payment"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {latestPayment?.plan_name ?? "Choose a membership plan to begin."}
            </p>
          </article>
          <article className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <ReceiptText className="size-6 text-primary" aria-hidden />
            <h2 className="mt-4 text-lg font-semibold">Latest invoice</h2>
            <p className="mt-2 text-2xl font-bold">
              {latestInvoice ? latestInvoice.invoice_number : "No invoice"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {latestInvoice
                ? `Expires ${formatDate(latestInvoice.membership_expiry_date)}`
                : "Invoices appear after purchase."}
            </p>
          </article>
          <article className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <UserCog className="size-6 text-accent" aria-hidden />
            <h2 className="mt-4 text-lg font-semibold">Account</h2>
            <p className="mt-2 text-2xl font-bold">{user?.tier}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {user?.is_email_verified ? "Verified email" : "Email pending"}
            </p>
          </article>
        </section>

        <section className="mt-6 grid gap-3 sm:grid-cols-3">
          <ButtonLink asChild>
            <Link to="/memberships">View plans</Link>
          </ButtonLink>
          <ButtonLink asChild variant="outline">
            <Link to="/billing">Payment history</Link>
          </ButtonLink>
          <ButtonLink asChild variant="outline">
            <Link to="/profile">Profile settings</Link>
          </ButtonLink>
        </section>

        <EmptyState
          className="mt-6"
          title="Attendance and class booking stay out of this slice"
          message="QR scanning and classes begin after Day 20, so this dashboard keeps those areas as safe placeholders."
        />
      </main>
    </AppFrame>
  );
}
