import { ArrowRight, CalendarDays, ClipboardCheck, ClipboardList, CreditCard, Dumbbell, Megaphone, Settings2, ShieldCheck, UsersRound } from "lucide-react";
import { Link } from "react-router-dom";

import { AdminShell } from "@/components/layout/AdminShell";
import { useAuth } from "@/features/auth/AuthContext";

const areas = [
  { title: "Member CRM", detail: "Search, filter, export, and review complete real member records.", to: "/admin/members", icon: UsersRound, roles: ["admin"] },
  { title: "Billing ledger", detail: "Filtered payments, invoices, audited exports, and totals.", to: "/admin/billing", icon: CreditCard, roles: ["admin"] },
  { title: "Attendance ops", detail: "Live capacity, session controls, event sources, and peak-hours analytics.", to: "/admin/attendance", icon: ClipboardList, roles: ["staff", "manager", "admin"] },
  { title: "Class schedule", detail: "Create, edit, filter, and cancel trainer-linked classes.", to: "/admin/classes", icon: CalendarDays, roles: ["admin"] },
  { title: "PT profiles", detail: "Maintain member-facing coach profiles and future class assignments.", to: "/admin/pt-assignments", icon: Dumbbell, roles: ["manager", "admin"] },
  { title: "YPTrain exercises", detail: "Maintain the shared member exercise guide, muscle tags and images.", to: "/admin/exercises", icon: Dumbbell, roles: ["manager", "admin"] },
  { title: "Membership approvals", detail: "Review freeze and cancellation requests with required reasons and outcomes.", to: "/admin/approvals", icon: ClipboardCheck, roles: ["manager", "admin"] },
  { title: "Broadcasts", detail: "Publish preference-aware announcements with active periods.", to: "/admin/broadcasts", icon: Megaphone, roles: ["manager", "admin"] },
  { title: "Audit log", detail: "Review sensitive actions, actors, targets, reasons, and outcomes.", to: "/admin/audit", icon: ShieldCheck, roles: ["manager", "admin"] },
  { title: "Configuration", detail: "Manage validated runtime values with Redis cache invalidation.", to: "/admin/settings", icon: Settings2, roles: ["manager", "admin"] },
];

export function AdminDashboardPage() {
  const { user } = useAuth();
  const visibleAreas = areas.filter((area) => user && area.roles.includes(user.role));
  return <AdminShell>
    <div className="mx-auto max-w-6xl"><p className="page-kicker">Operations workspace</p><h1 className="page-title">Run the gym,<br />with evidence.</h1><p className="page-description">Your dashboard shows only the connected CRM, billing, attendance, classes, YPTrain, communication, audit and configuration areas approved for your role.</p><section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{visibleAreas.map((area, index) => { const Icon = area.icon; const featured = index === 0; return <Link className={`min-h-56 rounded-[1.2rem] border p-5 transition hover:-translate-y-1 ${featured ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card"}`} to={area.to} key={area.title}><span className={`grid size-10 place-items-center rounded-xl ${featured ? "bg-secondary text-foreground" : "bg-muted text-muted-foreground"}`}><Icon className="size-5" aria-hidden /></span><p className={`mt-7 text-[10px] font-extrabold uppercase tracking-[0.14em] ${featured ? "text-secondary" : "text-muted-foreground"}`}>Connected operation</p><h2 className="mt-2 font-['Barlow_Condensed'] text-3xl font-bold uppercase leading-none">{area.title}</h2><p className={`mt-3 text-xs leading-6 ${featured ? "text-primary-foreground/70" : "text-muted-foreground"}`}>{area.detail}</p><ArrowRight className={`mt-5 size-4 ${featured ? "text-secondary" : "text-primary"}`} aria-hidden /></Link>; })}</section></div>
  </AdminShell>;
}
