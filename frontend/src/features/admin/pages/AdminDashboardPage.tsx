import { BarChart3, ClipboardList, Users } from "lucide-react";

import { PermissionState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";

const adminCards = [
  { title: "CRM", value: "Member records pending", icon: Users },
  { title: "Operations", value: "Attendance oversight pending", icon: ClipboardList },
  { title: "Analytics", value: "Reports pending", icon: BarChart3 },
];

export function AdminDashboardPage() {
  return (
    <AppFrame>
      <main className="mx-auto max-w-6xl px-5 py-10">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <p className="mt-2 text-muted-foreground">
            Admin routes are ready for CRM, billing, attendance, and analytics.
          </p>
        </div>
        <section className="grid gap-4 md:grid-cols-3">
          {adminCards.map((card) => (
            <article
              key={card.title}
              className="rounded-lg border border-border bg-card p-5 shadow-sm"
            >
              <card.icon className="size-6 text-accent" aria-hidden />
              <h2 className="mt-4 text-lg font-semibold">{card.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {card.value}
              </p>
            </article>
          ))}
        </section>
        <PermissionState
          className="mt-6"
          title="Role checks coming next"
          message="Admin pages now share a consistent permission state while RBAC is implemented in the next milestone."
        />
      </main>
    </AppFrame>
  );
}
