import { ArrowLeft, LockKeyhole } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

import { AppFrame } from "@/components/layout/AppFrame";
import { useAuth } from "@/features/auth/AuthContext";

export function PermissionDeniedPage() {
  const { user } = useAuth();
  const location = useLocation();
  const home = user?.role === "pt" ? "/pt/dashboard" : ["admin", "manager", "staff"].includes(user?.role ?? "") ? "/admin" : "/app/dashboard";
  const from = (location.state as { from?: string } | null)?.from;

  return (
    <AppFrame>
      <main id="main-content" className="mx-auto grid min-h-[calc(100vh-4.8rem)] max-w-4xl place-items-center px-5 py-10">
        <section className="surface-card max-w-xl p-8 text-center sm:p-12">
          <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-accent/15 text-accent"><LockKeyhole className="size-6" aria-hidden /></span>
          <p className="page-kicker mt-6">Permission required</p>
          <h1 className="mt-2 font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-none">This route is not part of your workspace.</h1>
          <p className="mt-5 text-sm leading-7 text-muted-foreground">{from ? `Your ${user?.role ?? "current"} role cannot access ${from}.` : "Your current role does not have access to this page."}</p>
          <Link className="mt-7 inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-extrabold text-primary-foreground" to={home}><ArrowLeft className="size-4" aria-hidden /> Back to workspace</Link>
        </section>
      </main>
    </AppFrame>
  );
}
