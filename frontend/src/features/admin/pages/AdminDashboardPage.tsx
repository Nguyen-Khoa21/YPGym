import { ArrowRight, ClipboardList, CreditCard, UsersRound } from "lucide-react";
import { Link } from "react-router-dom";

import { AdminShell } from "@/components/layout/AdminShell";

const areas = [
  { title: "Billing ledger", detail: "Live payment records from the existing admin endpoint.", to: "/admin/billing", icon: CreditCard, live: true },
  { title: "Member CRM", detail: "Search and member record APIs are not connected yet.", to: "/admin/members", icon: UsersRound, live: false },
  { title: "Attendance ops", detail: "QR scans and occupancy data start with the attendance module.", to: "/admin/attendance", icon: ClipboardList, live: false },
];

export function AdminDashboardPage() {
  return <AdminShell>
    <div className="mx-auto max-w-6xl"><p className="page-kicker">Operations workspace</p><h1 className="page-title">Run the gym,<br />without the fiction.</h1><p className="page-description">This admin shell is ready for the future CRM and operations modules. In the current release, it exposes only the billing data that the backend actually provides.</p><section className="mt-8 grid gap-4 md:grid-cols-3">{areas.map((area) => { const Icon = area.icon; return <Link className={`min-h-56 rounded-[1.2rem] border p-5 transition hover:-translate-y-1 ${area.live ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card"}`} to={area.to} key={area.title}><span className={`grid size-10 place-items-center rounded-xl ${area.live ? "bg-secondary text-foreground" : "bg-muted text-muted-foreground"}`}><Icon className="size-5" aria-hidden /></span><p className={`mt-7 text-[10px] font-extrabold uppercase tracking-[0.14em] ${area.live ? "text-secondary" : "text-muted-foreground"}`}>{area.live ? "Connected today" : "Planned route"}</p><h2 className="mt-2 font-['Barlow_Condensed'] text-3xl font-bold uppercase leading-none">{area.title}</h2><p className={`mt-3 text-xs leading-6 ${area.live ? "text-primary-foreground/70" : "text-muted-foreground"}`}>{area.detail}</p><ArrowRight className={`mt-5 size-4 ${area.live ? "text-secondary" : "text-primary"}`} aria-hidden /></Link>; })}</section><div className="mt-7 rounded-2xl border border-border bg-card p-5 text-sm leading-6"><strong>Current boundary:</strong> member CRM, attendance, classes, PT assignment and notifications have no backend implementation in this pass. Their navigation entries point to explicit planned states only.</div></div>
  </AdminShell>;
}
