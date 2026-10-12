import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock3, ReceiptText, RefreshCw, XCircle } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { shouldPollPayment } from "@/features/billing/paymentFlow";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDate, formatMoney } from "@/lib/format";
import type { PaymentStatus } from "@/types/api";

export function PaymentResultPage() {
  const { token } = useAuth();
  const [search] = useSearchParams();
  const transactionId = search.get("transaction_id") ?? sessionStorage.getItem("ypgym:vnpay:last-transaction");
  const returnState = search.get("state");
  const [timedOutTransaction, setTimedOutTransaction] = useState<string | null>(null);
  const timedOut = timedOutTransaction === transactionId;
  useEffect(() => {
    const timer = window.setTimeout(() => setTimedOutTransaction(transactionId), 30_000);
    return () => window.clearTimeout(timer);
  }, [transactionId]);
  const payment = useQuery({
    queryKey: ["payment", transactionId],
    queryFn: ({ signal }) => apiRequest<PaymentStatus>(`/payments/${transactionId}`, { token, signal }),
    enabled: Boolean(transactionId && returnState !== "invalid"),
    retry: false,
    refetchInterval: (query) => shouldPollPayment((query.state.data as PaymentStatus | undefined)?.status, timedOut) ? 2_000 : false,
  });

  if (!transactionId || returnState === "invalid") return <MemberShell><ResultCard tone="error" title="Payment response could not be verified" detail="Return to the product page and start a new VNPay checkout." action={<LinkButton to="/app/billing">View billing</LinkButton>} /></MemberShell>;
  if (payment.isLoading) return <MemberShell><LoadingState title="Checking VNPay confirmation" /></MemberShell>;
  if (payment.isError) return <MemberShell><ErrorState title={toUiError(payment.error).title} message={toUiError(payment.error).message} action={<Button variant="outline" onClick={() => payment.refetch()}><RefreshCw className="size-4" />Retry status check</Button>} /></MemberShell>;

  const result = payment.data!;
  if (result.status === "paid") return <MemberShell><ResultCard tone="success" title={result.product_type === "class_booking" ? "Class booking confirmed" : "Membership payment confirmed"} detail={`VNPay confirmed ${formatMoney(result.amount_vnd)} for ${result.product_name}.`} body={<div className="grid gap-3 sm:grid-cols-2">{result.product_type === "class_booking" ? <><Detail label="Booking status" value={result.booking_status ?? "confirmed"} /><Detail label="Session" value={result.class_start_at ? formatDate(result.class_start_at) : "Scheduled"} /></> : <><Detail label="Membership status" value={result.membership_status ?? "active"} /><Detail label="Coverage expiry" value={result.membership_expiry_date ? formatDate(result.membership_expiry_date) : "Updating"} />{result.discount_details ? <><Detail label="Applied discount" value={`${Number(result.discount_details.pricing.applied_discount_percent)}%`} /><Detail label="Previous-month visits" value={`${result.discount_details.attended_days}/${result.discount_details.period_days}`} /></> : null}</>}</div>} action={<div className="flex flex-wrap gap-3">{result.invoice_id ? <LinkButton to="/app/billing"><ReceiptText className="size-4" />View invoice</LinkButton> : null}<LinkButton to={result.product_type === "class_booking" ? "/app/bookings" : "/app/dashboard"}>{result.product_type === "class_booking" ? "My bookings" : "Member dashboard"}</LinkButton></div>} /></MemberShell>;
  if (result.status === "paid_review") return <MemberShell><ResultCard tone="processing" title="Payment received — staff review required" detail="VNPay reported payment after the seat hold could no longer be fulfilled. No extra seat was confirmed; staff will resolve the refund." action={<LinkButton to="/app/billing">View payment record</LinkButton>} /></MemberShell>;
  if (["failed", "cancelled", "expired"].includes(result.status)) return <MemberShell><ResultCard tone="error" title={result.status === "cancelled" ? "Payment cancelled" : result.status === "expired" ? "Payment expired" : "Payment unsuccessful"} detail={result.product_type === "class_booking" ? "No class seat was confirmed. Start a fresh checkout when you are ready." : "Your membership was not changed. Start a fresh checkout when you are ready."} action={<LinkButton to={result.product_type === "class_booking" ? "/app/classes" : `/memberships/buy/${result.membership_plan_id}`}>Try VNPay again</LinkButton>} /></MemberShell>;

  return <MemberShell><ResultCard tone="processing" title={timedOut ? "Confirmation is taking longer" : "Payment confirmation pending"} detail={timedOut ? "VNPay may still deliver the confirmation. You can check again without repeating the payment." : "Keep this page open while YPGym waits for VNPay's signed server confirmation."} action={<Button variant="outline" onClick={() => payment.refetch()}><RefreshCw className="size-4" />Check again</Button>} /></MemberShell>;
}

function ResultCard({ tone, title, detail, body, action }: { tone: "success" | "error" | "processing"; title: string; detail: string; body?: ReactNode; action: ReactNode }) {
  const Icon = tone === "success" ? CheckCircle2 : tone === "error" ? XCircle : Clock3;
  return <section className="mx-auto max-w-3xl"><article className="surface-card p-7 sm:p-10" aria-live="polite"><span className={`grid size-14 place-items-center rounded-2xl ${tone === "success" ? "bg-secondary text-primary" : tone === "error" ? "bg-destructive/10 text-destructive" : "bg-muted text-primary"}`}><Icon className="size-7" aria-hidden /></span><h1 className="mt-6 font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-none">{title}</h1><p className="mt-4 text-sm leading-7 text-muted-foreground">{detail}</p>{body ? <div className="mt-7">{body}</div> : null}<div className="mt-7">{action}</div></article></section>;
}

function LinkButton({ to, children }: { to: string; children: ReactNode }) { return <Link className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-extrabold text-primary-foreground" to={to}>{children}</Link>; }
function Detail({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-border bg-card p-4"><p className="text-[10px] font-extrabold uppercase tracking-[0.12em] text-muted-foreground">{label}</p><p className="mt-2 text-sm font-extrabold capitalize">{value}</p></div>; }
