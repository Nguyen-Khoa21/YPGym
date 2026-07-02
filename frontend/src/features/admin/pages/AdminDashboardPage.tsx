import { BarChart3, ClipboardList, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { ButtonLink } from "@/components/ui/Button";

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
            Admin routes are role protected. Billing has a Day 20 placeholder
            table; full CRM work starts later.
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
        <div className="mt-6">
          <ButtonLink asChild>
            <Link to="/admin/billing">Open billing placeholder</Link>
          </ButtonLink>
        </div>
        <EmptyState
          className="mt-6"
          title="Full admin CRM is not in Day 11-20"
          message="Member CRM, QR attendance, cancellations, and notifications remain outside this implementation window."
        />
      </main>
    </AppFrame>
  );
}
