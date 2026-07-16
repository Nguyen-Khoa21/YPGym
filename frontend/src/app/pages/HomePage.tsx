import {
  ArrowRight,
  CalendarDays,
  CreditCard,
  QrCode,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router-dom";

import { AppFrame } from "@/components/layout/AppFrame";

const highlights = [
  { title: "Choose your rhythm", copy: "Six real membership plans, with pricing calculated by the backend.", icon: ShieldCheck },
  { title: "Keep every receipt", copy: "Payments and downloadable invoices stay attached to your account.", icon: CreditCard },
  { title: "Train with clarity", copy: "QR and class features are visible as planned work, never simulated data.", icon: QrCode },
];

export function HomePage() {
  return (
    <AppFrame>
      <main id="main-content">
        <section className="relative overflow-hidden border-b border-border bg-primary">
          <div className="absolute -right-20 -top-28 size-[28rem] rounded-full border-[54px] border-secondary/20" aria-hidden />
          <div className="absolute bottom-0 left-[47%] h-32 w-px bg-secondary/30" aria-hidden />
          <div className="relative mx-auto grid max-w-7xl gap-10 px-5 py-14 sm:px-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-end lg:py-24">
            <div className="max-w-3xl">
              <span className="inline-flex items-center gap-2 rounded-full border border-secondary/30 bg-secondary/10 px-3 py-1 text-xs font-extrabold uppercase tracking-[0.14em] text-secondary">
                <Sparkles className="size-3.5" aria-hidden /> Connected member portal
              </span>
              <h1 className="mt-5 max-w-3xl font-['Barlow_Condensed'] text-6xl font-bold uppercase leading-[0.82] tracking-tight text-primary-foreground sm:text-7xl lg:text-8xl">
                Train with a<br />
                <span className="text-secondary">clearer plan.</span>
              </h1>
              <p className="mt-7 max-w-xl text-base leading-8 text-primary-foreground/75">
                YPGym brings membership, account security, billing and invoices
                into one deliberate member experience.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link className="inline-flex items-center gap-2 rounded-full bg-secondary px-5 py-3 text-sm font-extrabold text-foreground transition hover:-translate-y-0.5" to="/memberships">
                  Explore memberships <ArrowRight className="size-4" aria-hidden />
                </Link>
                <Link className="inline-flex items-center gap-2 rounded-full border border-primary-foreground/25 px-5 py-3 text-sm font-extrabold text-primary-foreground transition hover:bg-primary-foreground/10" to="/register">
                  Create an account
                </Link>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-md lg:justify-self-end">
              <div className="rounded-[1.6rem] border border-primary-foreground/15 bg-primary-foreground p-4 shadow-2xl shadow-black/20">
                <div className="flex items-center justify-between border-b border-border pb-4">
                  <span className="font-['Barlow_Condensed'] text-xl font-bold uppercase tracking-wide">Your next set</span>
                  <span className="rounded-full bg-secondary px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider">Member view</span>
                </div>
                <div className="mt-4 rounded-2xl bg-primary p-5 text-primary-foreground">
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-secondary">Membership status</p>
                  <p className="mt-3 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">Ready when<br />you are.</p>
                  <div className="mt-5 h-2 overflow-hidden rounded-full bg-primary-foreground/15">
                    <div className="h-full w-2/3 rounded-full bg-secondary" />
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-border p-3">
                    <CreditCard className="size-4 text-accent" aria-hidden />
                    <p className="mt-3 text-xs font-bold">Billing history</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">Connected now</p>
                  </div>
                  <div className="rounded-xl border border-border p-3">
                    <CalendarDays className="size-4 text-primary" aria-hidden />
                    <p className="mt-3 text-xs font-bold">Class booking</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">Planned Day 33+</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-20">
          <div className="max-w-xl">
            <p className="page-kicker">Built with the real system underneath</p>
            <h2 className="page-title">No pretend dashboards.</h2>
            <p className="page-description">Every live screen is tied to the API that supports it. The rest stays plainly marked until it is actually ready.</p>
          </div>
          <div className="mt-9 grid gap-4 md:grid-cols-3">
            {highlights.map((item, index) => (
              <article key={item.title} className="surface-card group p-6 transition duration-200 hover:-translate-y-1">
                <span className="flex size-10 items-center justify-center rounded-xl bg-secondary text-foreground">
                  <item.icon className="size-5" aria-hidden />
                </span>
                <p className="mt-6 text-xs font-extrabold uppercase tracking-[0.12em] text-muted-foreground">0{index + 1}</p>
                <h3 className="mt-2 text-2xl font-bold">{item.title}</h3>
                <p className="mt-3 text-sm leading-7 text-muted-foreground">{item.copy}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </AppFrame>
  );
}
