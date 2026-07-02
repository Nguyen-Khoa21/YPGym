import { useQuery } from "@tanstack/react-query";
import { Download, ReceiptText } from "lucide-react";
import { Link } from "react-router-dom";

import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { Button, ButtonLink } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest, apiUrl } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDate, formatDateTime, formatMoney } from "@/lib/format";
import type { InvoiceHistoryItem, PaymentHistoryItem } from "@/types/api";

export function PaymentHistoryPage() {
  const { token } = useAuth();
  const payments = useQuery({
    queryKey: ["billing", "payments"],
    queryFn: () =>
      apiRequest<PaymentHistoryItem[]>("/billing/me/payments", { token }),
  });
  const invoices = useQuery({
    queryKey: ["billing", "invoices"],
    queryFn: () =>
      apiRequest<InvoiceHistoryItem[]>("/billing/me/invoices", { token }),
  });

  const isLoading = payments.isLoading || invoices.isLoading;
  const firstError = payments.error || invoices.error;

  async function downloadInvoice(invoice: InvoiceHistoryItem) {
    const response = await fetch(apiUrl(invoice.download_url), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error("Invoice download failed.");
    }
    const blob = await response.blob();
    const href = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = `${invoice.invoice_number}.pdf`;
    anchor.click();
    window.URL.revokeObjectURL(href);
  }

  return (
    <AppFrame>
      <main className="mx-auto max-w-6xl px-5 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-primary">
              Billing
            </p>
            <h1 className="mt-2 text-3xl font-bold">Payment and Invoice History</h1>
            <p className="mt-2 text-muted-foreground">
              Review mock payments and download immutable membership invoices.
            </p>
          </div>
          <ButtonLink asChild variant="outline">
            <Link to="/memberships">Buy or renew</Link>
          </ButtonLink>
        </div>

        {isLoading ? <LoadingState title="Loading billing history" /> : null}

        {firstError ? (
          <ErrorState
            title={toUiError(firstError).title}
            message={toUiError(firstError).message}
          />
        ) : null}

        {!isLoading && !firstError ? (
          <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            <section>
              <h2 className="mb-3 text-xl font-bold">Payments</h2>
              {payments.data?.length ? (
                <div className="space-y-3">
                  {payments.data.map((payment) => (
                    <article
                      key={payment.id}
                      className="rounded-lg border border-border bg-card p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-bold">{payment.plan_name}</h3>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {payment.mock_reference} · {formatDateTime(payment.created_at)}
                          </p>
                        </div>
                        <span className="rounded-md bg-secondary/10 px-2 py-1 text-xs font-bold text-secondary">
                          {payment.status}
                        </span>
                      </div>
                      <p className="mt-4 text-2xl font-bold">
                        {formatMoney(payment.amount)}
                      </p>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="No payments yet"
                  message="Purchase a membership to create a payment record."
                />
              )}
            </section>

            <section>
              <h2 className="mb-3 text-xl font-bold">Invoices</h2>
              {invoices.data?.length ? (
                <div className="space-y-3">
                  {invoices.data.map((invoice) => (
                    <article
                      key={invoice.id}
                      className="rounded-lg border border-border bg-card p-4 shadow-sm"
                    >
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <ReceiptText className="size-4 text-primary" aria-hidden />
                            <h3 className="font-bold">{invoice.invoice_number}</h3>
                          </div>
                          <p className="mt-2 text-sm text-muted-foreground">
                            {invoice.plan_name} · {formatDate(invoice.membership_start_date)} to{" "}
                            {formatDate(invoice.membership_expiry_date)}
                          </p>
                          <p className="mt-3 text-xl font-bold">
                            {formatMoney(invoice.amount)}
                          </p>
                        </div>
                        <Button
                          variant="outline"
                          onClick={() => void downloadInvoice(invoice)}
                        >
                          <Download className="size-4" aria-hidden />
                          Download
                        </Button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="No invoices yet"
                  message="Successful membership purchases generate invoices here."
                />
              )}
            </section>
          </div>
        ) : null}
      </main>
    </AppFrame>
  );
}
