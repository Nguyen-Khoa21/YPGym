import { CalendarClock, Dumbbell, ShieldCheck } from "lucide-react";

import { AppFrame } from "@/components/layout/AppFrame";

export function PtDashboardPage() {
  return <AppFrame>
    <main id="main-content" className="mx-auto grid min-h-[calc(100vh-4.8rem)] max-w-5xl place-items-center px-5 py-10">
      <section className="w-full overflow-hidden rounded-[1.5rem] bg-primary text-primary-foreground"><div className="grid gap-7 p-7 sm:p-10 lg:grid-cols-[0.7fr_1.3fr] lg:items-center"><span className="grid aspect-square max-w-48 place-items-center rounded-[1.3rem] bg-secondary text-foreground"><Dumbbell className="size-14" aria-hidden /></span><div><p className="text-xs font-extrabold uppercase tracking-[0.14em] text-secondary">PT workspace</p><h1 className="mt-3 font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-[0.86]">Your trainer home is ready for the next module.</h1><p className="mt-5 max-w-xl text-sm leading-7 text-primary-foreground/70">This is the safe post-login destination for personal trainers. It does not invent schedules, members or assignments before those APIs exist.</p><div className="mt-7 grid gap-3 sm:grid-cols-2"><div className="rounded-xl border border-primary-foreground/15 p-4"><CalendarClock className="size-5 text-secondary" aria-hidden /><p className="mt-3 text-sm font-bold">Schedule</p><p className="mt-1 text-xs text-primary-foreground/65">Planned Day 33+</p></div><div className="rounded-xl border border-primary-foreground/15 p-4"><ShieldCheck className="size-5 text-secondary" aria-hidden /><p className="mt-3 text-sm font-bold">Assignments</p><p className="mt-1 text-xs text-primary-foreground/65">Planned Day 35+</p></div></div></div></div>
      </section>
    </main>
  </AppFrame>;
}
