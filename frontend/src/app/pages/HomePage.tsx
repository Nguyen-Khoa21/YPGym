import { Activity, CalendarDays, Dumbbell, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { AppFrame } from "@/components/layout/AppFrame";

const foundationItems = [
  {
    title: "Memberships",
    description: "Plans, renewals, billing, and lifecycle status.",
    icon: ShieldCheck,
  },
  {
    title: "Attendance",
    description: "QR entry, occupancy, and crowdedness tracking.",
    icon: Activity,
  },
  {
    title: "Classes",
    description: "Schedules, trainer profiles, bookings, and waitlists.",
    icon: CalendarDays,
  },
  {
    title: "Personalization",
    description: "Preferences, recommendations, and guided support.",
    icon: Dumbbell,
  },
];

export function HomePage() {
  return (
    <AppFrame>
      <section className="mx-auto grid max-w-6xl gap-8 px-5 py-10 md:grid-cols-[1.1fr_0.9fr] md:items-center md:py-16">
        <div className="space-y-6">
          <div className="inline-flex rounded-md border border-border bg-card px-3 py-1 text-sm font-medium text-muted-foreground">
            Foundation sprint
          </div>
          <div className="space-y-4">
            <h1 className="max-w-3xl text-4xl font-bold leading-tight text-foreground md:text-5xl">
              YPGym
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-muted-foreground">
              A focused gym management workspace for members, attendance,
              classes, billing, CRM, and future AI-assisted support.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/member"
              className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90"
            >
              Member Area
            </Link>
            <Link
              to="/admin"
              className="rounded-md border border-border bg-card px-4 py-2 text-sm font-semibold shadow-sm transition hover:bg-muted"
            >
              Admin Area
            </Link>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {foundationItems.map((item) => (
            <article
              key={item.title}
              className="rounded-lg border border-border bg-card p-4 shadow-sm"
            >
              <item.icon className="mb-4 size-6 text-primary" aria-hidden />
              <h2 className="text-base font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {item.description}
              </p>
            </article>
          ))}
        </div>
      </section>
    </AppFrame>
  );
}
