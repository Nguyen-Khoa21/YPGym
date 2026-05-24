import { CalendarDays, CreditCard, QrCode } from "lucide-react";

import { AppFrame } from "@/components/layout/AppFrame";

const memberCards = [
  { title: "Membership", value: "Pending setup", icon: CreditCard },
  { title: "Attendance", value: "QR module pending", icon: QrCode },
  { title: "Classes", value: "Booking module pending", icon: CalendarDays },
];

export function MemberDashboardPage() {
  return (
    <AppFrame>
      <main className="mx-auto max-w-6xl px-5 py-10">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Member Dashboard</h1>
          <p className="mt-2 text-muted-foreground">
            Member-facing routes are ready for upcoming modules.
          </p>
        </div>
        <section className="grid gap-4 md:grid-cols-3">
          {memberCards.map((card) => (
            <article
              key={card.title}
              className="rounded-lg border border-border bg-card p-5 shadow-sm"
            >
              <card.icon className="size-6 text-secondary" aria-hidden />
              <h2 className="mt-4 text-lg font-semibold">{card.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {card.value}
              </p>
            </article>
          ))}
        </section>
      </main>
    </AppFrame>
  );
}
