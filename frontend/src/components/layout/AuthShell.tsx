import type { PropsWithChildren, ReactNode } from "react";
import { Activity, ShieldCheck } from "lucide-react";

import { AppFrame } from "@/components/layout/AppFrame";

type AuthShellProps = PropsWithChildren<{
  eyebrow: string;
  title: ReactNode;
  description: string;
  detail?: string;
}>;

export function AuthShell({
  eyebrow,
  title,
  description,
  detail = "Your account actions are validated by the YPGym API.",
  children,
}: AuthShellProps) {
  return (
    <AppFrame compact>
      <main id="main-content" className="grid min-h-[calc(100vh-4.8rem)] bg-[radial-gradient(circle_at_0%_0%,hsl(var(--secondary)/0.22),transparent_24rem)] lg:grid-cols-[0.95fr_1.05fr]">
        <section className="relative overflow-hidden bg-primary px-6 py-12 text-primary-foreground sm:px-10 lg:flex lg:min-h-full lg:flex-col lg:justify-between lg:px-[clamp(2.5rem,7vw,8rem)] lg:py-16">
          <div className="absolute -bottom-24 -right-24 size-80 rounded-full border-[42px] border-secondary/20" aria-hidden />
          <div className="relative">
            <span className="inline-flex items-center gap-2 rounded-full bg-secondary px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-[0.14em] text-foreground"><Activity className="size-3.5" aria-hidden /> {eyebrow}</span>
            <h1 className="mt-7 max-w-lg font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-[0.86] sm:text-6xl">{title}</h1>
            <p className="mt-5 max-w-md text-sm leading-7 text-primary-foreground/75">{description}</p>
          </div>
          <div className="relative mt-10 flex max-w-sm gap-3 border-t border-primary-foreground/20 pt-5 text-xs leading-5 text-primary-foreground/70 lg:mt-0">
            <ShieldCheck className="size-5 shrink-0 text-secondary" aria-hidden />
            <p>{detail}</p>
          </div>
        </section>
        <section className="flex items-center justify-center px-5 py-10 sm:px-8 lg:px-[clamp(2.5rem,6vw,7rem)]">
          <div className="w-full max-w-md">{children}</div>
        </section>
      </main>
    </AppFrame>
  );
}
