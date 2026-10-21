import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import { navigationForRole, operationsNavigation } from "@/app/navigation";
import { AdminShell } from "@/components/layout/AdminShell";
import { useAuth } from "@/features/auth/AuthContext";

export function AdminDashboardPage() {
  const { user } = useAuth();
  const visibleAreas = navigationForRole(operationsNavigation, user?.role).filter((item) => item.dashboard);
  return <AdminShell>
    <div className="mx-auto max-w-6xl"><p className="page-kicker">Operations workspace</p><h1 className="page-title">Run the gym,<br />with evidence.</h1><p className="page-description">Your dashboard shows only the connected CRM, billing, attendance, classes, YPTrain, communication, audit and configuration areas approved for your role.</p><section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{visibleAreas.map((area, index) => { const Icon = area.icon; const featured = index === 0; return <Link className={`min-h-56 rounded-[1.2rem] border p-5 transition hover:-translate-y-1 ${featured ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card"}`} to={area.to} key={area.to}><span className={`grid size-10 place-items-center rounded-xl ${featured ? "bg-secondary text-foreground" : "bg-muted text-muted-foreground"}`}><Icon className="size-5" aria-hidden /></span><p className={`mt-7 text-[10px] font-extrabold uppercase tracking-[0.14em] ${featured ? "text-secondary" : "text-muted-foreground"}`}>Connected operation</p><h2 className="mt-2 font-['Barlow_Condensed'] text-3xl font-bold uppercase leading-none">{area.dashboard!.title}</h2><p className={`mt-3 text-xs leading-6 ${featured ? "text-primary-foreground/70" : "text-muted-foreground"}`}>{area.dashboard!.detail}</p><ArrowRight className={`mt-5 size-4 ${featured ? "text-secondary" : "text-primary"}`} aria-hidden /></Link>; })}</section></div>
  </AdminShell>;
}
