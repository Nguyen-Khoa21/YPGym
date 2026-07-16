import { ArrowRight, BadgeCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { AppFrame } from "@/components/layout/AppFrame";

export function VerificationSuccessPage() {
  return (
    <AppFrame compact>
      <main id="main-content" className="mx-auto grid min-h-[calc(100vh-4.8rem)] max-w-xl place-items-center px-5 py-10">
        <section className="form-card p-8 text-center sm:p-10">
          <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-secondary text-foreground"><BadgeCheck className="size-7" aria-hidden /></span>
          <p className="page-kicker mt-6">Email verified</p>
          <h1 className="mt-2 font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-none">Your account is ready.</h1>
          <p className="mt-5 text-sm leading-7 text-muted-foreground">Sign in with your verified email to choose a membership plan and access your account.</p>
          <Link className="mt-7 inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-extrabold text-primary-foreground" to="/login">Continue to login <ArrowRight className="size-4" aria-hidden /></Link>
        </section>
      </main>
    </AppFrame>
  );
}
