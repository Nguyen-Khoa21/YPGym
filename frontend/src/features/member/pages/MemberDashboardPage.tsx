import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarDays, CreditCard, QrCode, ReceiptText, UserRoundCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDate, formatMoney } from "@/lib/format";
import type { InvoiceHistoryItem, PaymentHistoryItem } from "@/types/api";

export function MemberDashboardPage() {
  const { user, token } = useAuth();
  const payments = useQuery({ queryKey: ["dashboard", "payments"], enabled: Boolean(token), queryFn: ({ signal }) => apiRequest<PaymentHistoryItem[]>("/billing/me/payments", { token, signal }) });
  const invoices = useQuery({ queryKey: ["dashboard", "invoices"], enabled: Boolean(token), queryFn: ({ signal }) => apiRequest<InvoiceHistoryItem[]>("/billing/me/invoices", { token, signal }) });
  const latestPayment = payments.data?.[0];
  const latestInvoice = invoices.data?.[0];
  const firstError = payments.error || invoices.error;

  return <MemberShell>
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="page-kicker">Member dashboard</p><h1 className="page-title">Good to see you, {user?.name.split(" ")[0]}.</h1><p className="page-description">Your live billing and account summary, with future training features clearly held back until their APIs arrive.</p></div><Link className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2.5 text-sm font-extrabold text-primary-foreground" to="/memberships">Explore plans <ArrowRight className="size-4" aria-hidden /></Link></div>
      {payments.isLoading || invoices.isLoading ? <LoadingState className="mt-7" title="Loading your account summary" /> : null}
      {firstError ? <ErrorState className="mt-7" title={toUiError(firstError).title} message={toUiError(firstError).message} /> : null}
      {!payments.isLoading && !invoices.isLoading && !firstError ? <>
        <section className="mt-8 grid gap-4 md:grid-cols-3"><SummaryCard title="Latest payment" value={latestPayment ? formatMoney(latestPayment.amount) : "No payment"} detail={latestPayment?.plan_name ?? "Choose a membership plan to begin."} icon={CreditCard} tone="lime" /><SummaryCard title="Latest invoice" value={latestInvoice?.invoice_number ?? "No invoice"} detail={latestInvoice ? `Expires ${formatDate(latestInvoice.membership_expiry_date)}` : "Invoices appear after purchase."} icon={ReceiptText} tone="dark" /><SummaryCard title="Account" value={user?.tier ?? "Member"} detail={user?.is_email_verified ? "Verified email" : "Email verification pending"} icon={UserRoundCheck} tone="light" /></section>
        <section className="mt-7 grid gap-5 lg:grid-cols-[1.35fr_0.65fr]"><article className="surface-card overflow-hidden"><div className="flex flex-col gap-4 bg-primary p-6 text-primary-foreground sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-extrabold uppercase tracking-[0.13em] text-secondary">Membership & billing</p><h2 className="mt-2 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">The connected part of your portal.</h2></div><ReceiptText className="size-9 text-secondary" aria-hidden /></div><div className="grid gap-3 p-5 sm:grid-cols-2"><Link className="rounded-xl border border-border p-4 transition hover:bg-muted" to="/app/billing"><strong className="block text-sm">Payment history</strong><span className="mt-1 block text-xs leading-5 text-muted-foreground">Review payment records and download invoices.</span></Link><Link className="rounded-xl border border-border p-4 transition hover:bg-muted" to="/app/profile"><strong className="block text-sm">Profile settings</strong><span className="mt-1 block text-xs leading-5 text-muted-foreground">Update name, phone and password.</span></Link></div></article><div className="grid gap-4"><FutureShortcut to="/app/qr" title="My QR code" detail="Attendance module planned Day 30" icon={QrCode} /><FutureShortcut to="/app/classes" title="Classes" detail="Booking module planned Day 33" icon={CalendarDays} /></div></section>
      </> : null}
    </div>
  </MemberShell>;
}

function SummaryCard({ title, value, detail, icon: Icon, tone }: { title: string; value: string; detail: string; icon: typeof CreditCard; tone: "lime" | "dark" | "light" }) { const styles = { lime: "bg-secondary text-foreground", dark: "bg-primary text-primary-foreground", light: "bg-card text-foreground" }; return <article className={`min-h-48 rounded-[1.15rem] border border-border p-5 shadow-[0_1rem_3rem_-2.5rem_hsl(var(--foreground)/0.35)] ${styles[tone]}`}><Icon className={`size-5 ${tone === "dark" ? "text-secondary" : "text-primary"}`} aria-hidden /><p className={`mt-7 text-xs font-extrabold uppercase tracking-[0.12em] ${tone === "dark" ? "text-primary-foreground/65" : "text-muted-foreground"}`}>{title}</p><p className="mt-2 font-['Barlow_Condensed'] text-3xl font-bold uppercase leading-none">{value}</p><p className={`mt-3 text-xs leading-5 ${tone === "dark" ? "text-primary-foreground/70" : "text-muted-foreground"}`}>{detail}</p></article>; }
function FutureShortcut({ to, title, detail, icon: Icon }: { to: string; title: string; detail: string; icon: typeof QrCode }) { return <Link className="surface-card flex items-center gap-4 p-4 transition hover:-translate-y-0.5" to={to}><span className="grid size-10 place-items-center rounded-xl bg-muted text-muted-foreground"><Icon className="size-5" aria-hidden /></span><span className="min-w-0 flex-1"><strong className="block text-sm">{title}</strong><small className="block pt-0.5 text-xs text-muted-foreground">{detail}</small></span><span className="rounded-full bg-muted px-2 py-1 text-[9px] font-extrabold uppercase text-muted-foreground">Planned</span></Link>; }
