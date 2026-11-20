import { Gauge } from "lucide-react";

import { formatDateTime } from "@/lib/format";
import type { Crowdedness } from "@/types/operations";

/** Live occupancy of the member's home gym, kept compact so the traffic history stays above the fold. */
export function OccupancyCard({ data }: { data: Crowdedness }) {
  const percentage = Math.min(Math.max(data.percentage, 0), 100);
  return (
    <section
      className="rounded-2xl border border-border bg-card px-4 py-3"
      aria-labelledby="occupancy-heading"
    >
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <h2
            id="occupancy-heading"
            className="text-xs font-black uppercase tracking-wider text-muted-foreground"
          >
            Live occupancy
          </h2>
          <p className="mt-0.5 flex flex-wrap items-baseline gap-x-2">
            <span className="font-['Barlow_Condensed'] text-3xl font-bold uppercase leading-none">
              {data.percentage}%
            </span>
            <span className="text-xs font-bold">{data.status}</span>
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {data.active_count} of {data.capacity} places in use right now.
          </p>
        </div>
        <Gauge className="size-6 shrink-0 text-primary" aria-hidden />
      </div>
      <div
        className="mt-2 h-2 overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-label="Capacity used"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percentage}
      >
        <div className="h-full rounded-full bg-secondary" style={{ width: `${percentage}%` }} />
      </div>
      <p className="mt-1.5 text-[11px] text-muted-foreground">
        Updated {formatDateTime(data.calculated_at)}
      </p>
    </section>
  );
}
