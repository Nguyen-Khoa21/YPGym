import { useQuery } from "@tanstack/react-query";
import { Download, Eye, ReceiptText, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { InvoiceViewerDialog } from "@/features/billing/components/InvoiceViewerDialog";
import { invoiceFileName } from "@/features/billing/invoiceViewer";
import { apiRequest, downloadApiFile } from "@/lib/apiClient";
import { toUiError, type UiError } from "@/lib/apiErrors";
import { formatDate, formatDateTime, formatMoney } from "@/lib/format";
import type { InvoiceHistoryItem, PaymentHistoryItem } from "@/types/api";

export function PaymentHistoryPage() {
  const { token } = useAuth();
  const [viewing, setViewing] = useState<InvoiceHistoryItem | null>(null);
  const [downloadError, setDownloadError] = useState<UiError | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const payments = useQuery({ queryKey: ["billing", "payments"], queryFn: ({ signal }) => apiRequest<PaymentHistoryItem[]>("/billing/me/payments", { token, signal }) });
  const invoices = useQuery({ queryKey: ["billing", "invoices"], queryFn: ({ signal }) => apiRequest<InvoiceHistoryItem[]>("/billing/me/invoices", { token, signal }) });
  const isLoading = payments.isLoading || invoices.isLoading;
  const firstError = payments.error || invoices.error;

  async function downloadInvoice(invoice: InvoiceHistoryItem) {
    setDownloadError(null);
    setDownloadingId(invoice.id);
    try {
      const href = URL.createObjectURL(await downloadApiFile(invoice.download_url, token));
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download = invoiceFileName(invoice.invoice_number);
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(href);
    } catch (caught) {
      setDownloadError(toUiError(caught));
    } finally {
      setDownloadingId(null);
    }
  }

  return <MemberShell>
    <div className="mx-auto max-w-6xl"><div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="page-kicker">Billing archive</p><h1 className="page-title">Payments & invoices.</h1><p className="page-description">Membership and individual class purchases remain separate and traceable with invoice downloads.</p></div><Link className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2.5 text-sm font-extrabold text-primary-foreground" to="/memberships"><RefreshCw className="size-4" aria-hidden /> Buy or renew</Link></div>
      {isLoading ? <LoadingState className="mt-7" title="Loading billing history" /> : null}
      {downloadError ? <ErrorState className="mt-7" title={downloadError.title} message={downloadError.message} /> : null}
      {firstError ? <ErrorState className="mt-7" title={toUiError(firstError).title} message={toUiError(firstError).message} /> : null}
      {!isLoading && !firstError ? <div className="mt-8 grid gap-7 lg:grid-cols-[0.85fr_1.15fr]"><section><div className="mb-4 flex items-center justify-between"><h2 className="font-['Barlow_Condensed'] text-3xl font-bold uppercase">Payment history</h2><span className="rounded-full bg-muted px-2.5 py-1 text-[10px] font-extrabold uppercase text-muted-foreground">{payments.data?.length ?? 0} records</span></div>{payments.data?.length ? <div className="space-y-3">{payments.data.map((payment) => <article className="surface-card p-5" key={payment.id}><div className="flex items-start justify-between gap-3"><div><p className="font-bold">{payment.product_name}</p><p className="mt-1 text-xs uppercase text-primary">{payment.product_type.replace("_", " ")}</p><p className="mt-1 text-xs text-muted-foreground"><span className="uppercase">{payment.provider}</span> · {payment.reference} · {formatDateTime(payment.created_at)}</p></div><span className="rounded-full bg-secondary/25 px-2.5 py-1 text-[10px] font-extrabold uppercase text-foreground">{payment.status}</span></div><p className="mt-5 font-['Barlow_Condensed'] text-3xl font-bold uppercase leading-none">{formatMoney(payment.amount)}</p>{payment.discount_details ? <p className="mt-2 text-xs text-muted-foreground">Applied discount {Number(payment.discount_details.pricing.applied_discount_percent)}% · Previous-month visits {payment.discount_details.attended_days}/{payment.discount_details.period_days}</p> : null}</article>)}</div> : <EmptyState title="No payments yet" message="A membership or class purchase creates a payment record." />}</section>
        <section><div className="mb-4 flex items-center justify-between"><h2 className="font-['Barlow_Condensed'] text-3xl font-bold uppercase">Invoices</h2><span className="rounded-full bg-muted px-2.5 py-1 text-[10px] font-extrabold uppercase text-muted-foreground">PDF download</span></div>{invoices.data?.length ? <div className="space-y-3">{invoices.data.map((invoice) => <article className="surface-card p-5" key={invoice.id}><div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex items-center gap-2"><span className="grid size-8 place-items-center rounded-lg bg-primary text-secondary"><ReceiptText className="size-4" aria-hidden /></span><p className="font-bold">{invoice.invoice_number}</p></div><p className="mt-4 text-sm font-semibold">{invoice.product_name}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{invoice.product_type === "class_booking" && invoice.service_start_at ? formatDateTime(invoice.service_start_at) : invoice.membership_start_date && invoice.membership_expiry_date ? `${formatDate(invoice.membership_start_date)} to ${formatDate(invoice.membership_expiry_date)}` : "Purchase receipt"}</p><p className="mt-4 font-['Barlow_Condensed'] text-3xl font-bold uppercase leading-none">{formatMoney(invoice.amount)}</p>{invoice.discount_details ? <p className="mt-2 text-xs text-muted-foreground">Better-of discount {Number(invoice.discount_details.pricing.applied_discount_percent)}% · Attendance {invoice.discount_details.attended_days}/{invoice.discount_details.period_days} days</p> : null}</div><div className="flex flex-wrap gap-2"><Button variant="outline" className="rounded-full" onClick={() => setViewing(invoice)}><Eye className="size-4" aria-hidden />View</Button><Button variant="outline" className="rounded-full" disabled={downloadingId === invoice.id} onClick={() => void downloadInvoice(invoice)}><Download className="size-4" aria-hidden />{downloadingId === invoice.id ? "Preparing..." : "Download"}</Button></div></div></article>)}</div> : <EmptyState title="No invoices yet" message="Successful membership and class purchases generate invoices here." />}</section>
      </div> : null}
    </div>
    {viewing ? <InvoiceViewerDialog key={viewing.id} invoice={viewing} onClose={() => setViewing(null)} /> : null}
  </MemberShell>;
}
