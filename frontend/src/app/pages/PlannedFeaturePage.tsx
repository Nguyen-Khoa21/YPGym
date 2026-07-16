import { CalendarClock, Construction, QrCode, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { AdminShell } from "@/components/layout/AdminShell";
import { AppFrame } from "@/components/layout/AppFrame";
import { MemberShell } from "@/components/layout/MemberShell";

type PlannedFeaturePageProps = {
  title: string;
  description: string;
  plannedDay: string;
  scope: "member" | "admin" | "pt";
  kind?: "qr" | "classes" | "operations";
};

export function PlannedFeaturePage({
  title,
  description,
  plannedDay,
  scope,
  kind = "operations",
}: PlannedFeaturePageProps) {
  const Icon = kind === "qr" ? QrCode : kind === "classes" ? CalendarClock : Construction;
  const content = (
    <section className="mx-auto max-w-3xl pt-4">
      <span className="eyebrow-chip"><Sparkles className="size-3.5" aria-hidden /> Planned feature</span>
      <h1 className="page-title mt-5">{title}</h1>
      <p className="page-description">{description}</p>
      <article className="surface-card mt-8 overflow-hidden">
        <div className="grid min-h-64 place-items-center bg-primary p-9 text-center text-primary-foreground">
          <span className="grid size-16 place-items-center rounded-2xl bg-secondary text-foreground"><Icon className="size-8" aria-hidden /></span>
          <div>
            <p className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">Not connected yet</p>
            <p className="mt-3 max-w-md text-sm leading-6 text-primary-foreground/70">This navigation destination intentionally has no local sample data or mock actions.</p>
          </div>
        </div>
        <div className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-extrabold uppercase tracking-[0.12em] text-muted-foreground">Scheduled development</p>
            <p className="mt-1 text-lg font-bold">{plannedDay}</p>
          </div>
          <Link className="inline-flex items-center justify-center rounded-full border border-border px-4 py-2.5 text-sm font-extrabold transition hover:bg-muted" to={scope === "admin" ? "/admin" : scope === "pt" ? "/pt/dashboard" : "/app/dashboard"}>Return to connected workspace</Link>
        </div>
      </article>
    </section>
  );

  if (scope === "admin") return <AdminShell>{content}</AdminShell>;
  if (scope === "member") return <MemberShell>{content}</MemberShell>;
  return <AppFrame>{<main id="main-content" className="mx-auto min-h-[calc(100vh-4.8rem)] px-5 py-10">{content}</main>}</AppFrame>;
}
