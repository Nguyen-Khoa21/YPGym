import { ArrowUpRight, CheckCircle2, Clock3, ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";

import { AppFrame } from "@/components/layout/AppFrame";

const sections = [
  { id: "renewal", title: "Renewal & expiry", connected: true, body: "Membership duration, configured price and expiry are confirmed on the purchase receipt and invoice. Renewal extends from the current expiry while a membership remains eligible." },
  { id: "freeze", title: "Freeze eligibility", connected: true, body: "Verified members with active or expiring-soon access can submit a dated freeze request for up to 90 days. An administrator must approve it before the freeze takes effect." },
  { id: "cancellation", title: "Cancellation", connected: true, body: "Members can submit a reasoned cancellation request. An administrator records the decision and the approved financial outcome—refund, account credit or forfeit—in the audit trail." },
  { id: "refunds", title: "Refunds & credits", connected: false, body: "The administration workflow records an approved financial outcome, but automated payment-gateway refunds and account-credit settlement remain outside this release. Invoices remain immutable records." },
  { id: "qr", title: "QR check-in rules", connected: true, body: "Eligible verified members receive a short-lived rotating QR token. The scanner API rejects expired, superseded, invalid or ineligible tokens and guards duplicate scans." },
];

export function MembershipPoliciesPage() {
  return (
    <AppFrame>
      <main id="main-content" className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-16">
        <div className="grid gap-10 lg:grid-cols-[14rem_minmax(0,1fr)]">
          <aside className="lg:sticky lg:top-28 lg:h-fit">
            <p className="page-kicker">Member handbook</p>
            <h1 className="mt-2 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">Membership<br />policies</h1>
            <nav className="mt-7 grid gap-1 border-l border-border pl-3" aria-label="Policy contents">
              {sections.map((section) => (
                <a className="rounded-r-lg px-3 py-2 text-sm font-bold text-muted-foreground transition hover:bg-muted hover:text-foreground" href={`#${section.id}`} key={section.id}>
                  {section.title}
                </a>
              ))}
            </nav>
          </aside>

          <div>
            <div className="rounded-[1.5rem] bg-primary p-6 text-primary-foreground sm:p-9">
              <span className="eyebrow-chip"><CheckCircle2 className="size-3.5" aria-hidden /> Current portal policy</span>
              <h2 className="mt-5 max-w-2xl font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-[0.86] sm:text-6xl">Clear terms. Honest feature status.</h2>
              <p className="mt-5 max-w-xl text-sm leading-7 text-primary-foreground/75">This handbook reflects the connected membership, notification and attendance workflows through Day 38 and labels the remaining payment-settlement boundary explicitly.</p>
              <Link className="mt-6 inline-flex items-center gap-2 text-sm font-extrabold text-secondary" to="/memberships">View membership plans <ArrowUpRight className="size-4" aria-hidden /></Link>
            </div>

            <div className="mt-7 space-y-4">
              {sections.map((section, index) => (
                <section id={section.id} className="surface-card scroll-mt-28 p-6 sm:p-7" key={section.id}>
                  <div className="flex items-start gap-4">
                    <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-muted font-['Barlow_Condensed'] text-lg font-bold">0{index + 1}</span>
                    <div>
                      <h2 className="text-3xl font-bold">{section.title}</h2>
                      <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground">{section.body}</p>
                      <p className={`mt-4 inline-flex items-center gap-2 text-xs font-extrabold uppercase tracking-wide ${section.connected ? "text-primary" : "text-accent"}`}>{section.connected ? <CheckCircle2 className="size-3.5" aria-hidden /> : <Clock3 className="size-3.5" aria-hidden />}{section.connected ? "Connected workflow" : "Recorded outcome; settlement planned"}</p>
                    </div>
                  </div>
                </section>
              ))}
            </div>
            <div className="mt-6 flex gap-3 rounded-2xl border border-accent/30 bg-accent/10 p-5 text-sm leading-6">
              <ShieldAlert className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
              <p><strong>Need account help?</strong> Use the authenticated membership-request page for freezes or cancellations. Contact the gym directly when an approved refund or account credit must be settled outside the portal.</p>
            </div>
          </div>
        </div>
      </main>
    </AppFrame>
  );
}
