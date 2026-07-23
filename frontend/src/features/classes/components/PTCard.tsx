import { CalendarClock, Dumbbell, MapPin } from "lucide-react";

import { formatDateTime } from "@/lib/format";
import type { Trainer } from "@/types/operations";

export function PTCard({ trainer, compact = false }: { trainer: Trainer; compact?: boolean }) {
  return <article className="rounded-2xl border border-border bg-card p-5">
    <div className="flex items-start gap-4">
      <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-secondary text-foreground"><Dumbbell className="size-6" aria-hidden /></span>
      <div className="min-w-0"><p className="text-[10px] font-black uppercase tracking-[0.12em] text-primary">Personal trainer</p><h3 className="mt-1 text-xl font-bold">{trainer.display_name}</h3>{trainer.specialty ? <p className="mt-1 text-sm text-muted-foreground">{trainer.specialty}</p> : null}</div>
    </div>
    {!compact && trainer.bio ? <p className="mt-4 text-sm leading-6 text-muted-foreground">{trainer.bio}</p> : null}
    {trainer.availability_summary ? <p className="mt-4 flex items-start gap-2 text-xs leading-5"><CalendarClock className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />{trainer.availability_summary}</p> : null}
    {!compact && trainer.upcoming_classes.length ? <div className="mt-4 border-t border-border pt-4"><p className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">Upcoming classes</p><ul className="mt-2 grid gap-2">{trainer.upcoming_classes.map((item) => <li className="rounded-xl bg-muted/50 p-3 text-xs" key={item.id}><strong className="block text-sm">{item.title}</strong><span className="mt-1 flex items-center gap-1 text-muted-foreground"><MapPin className="size-3" aria-hidden />{item.location} / {formatDateTime(item.start_at)}</span></li>)}</ul></div> : null}
  </article>;
}
