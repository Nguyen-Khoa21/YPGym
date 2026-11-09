import type { UseQueryResult } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { Button } from "@/components/ui/Button";
import { toUiError } from "@/lib/apiErrors";
import { formatDate } from "@/lib/format";
import type { TrafficSummary, TrafficWindow } from "@/types/operations";
import { buildHistoryView, formatPercentage, INSUFFICIENT_DATA_TITLE } from "../memberDashboardLogic";

/** Last month's busiest and quietest windows plus the two-hour pattern for the member's gym. */
export function TrafficHistory({ query }: { query: UseQueryResult<TrafficSummary> }) {
  return <section className="rounded-2xl border border-border bg-card p-5 sm:p-6" aria-labelledby="history-heading">
    <h2 id="history-heading" className="text-lg font-bold">When is it quiet?</h2>
    <Body query={query} />
  </section>;
}

function Body({ query }: { query: UseQueryResult<TrafficSummary> }) {
  if (query.isLoading) return <LoadingState className="mt-4" title="Loading last month's pattern" />;
  if (query.isError) {
    const error = toUiError(query.error);
    return <ErrorState className="mt-4" title={error.title} message={error.message} action={<Button variant="outline" onClick={() => void query.refetch()}>Retry</Button>} />;
  }
  if (!query.data) return null;
  const summary = query.data;
  const view = buildHistoryView(summary);
  if (view.kind === "insufficient") {
    return <div className="mt-4 rounded-xl bg-muted/50 p-4"><p className="font-bold">{INSUFFICIENT_DATA_TITLE}</p><p className="mt-1 text-sm text-muted-foreground">{view.reason}</p></div>;
  }
  return <>
    <p className="mt-1 text-xs leading-5 text-muted-foreground">{summary.gym_name} · {formatDate(summary.period_start)} to {formatDate(summary.period_end)}. These are historical averages from last month, not predictions.{summary.contains_demo_data ? " Some of these figures come from demonstration data." : ""}</p>
    <div className="mt-4 grid gap-3 sm:grid-cols-2"><WindowCard title="Busiest time last month" window={view.busiest} /><WindowCard title="Quietest time last month" window={view.quietest} /></div>
    <div className="mt-5 h-64 w-full" role="img" aria-label="Average capacity used by two-hour window last month. The same values are listed below the chart.">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={view.rows} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" />
          <XAxis dataKey="shortLabel" interval={0} tick={{ fontSize: 11 }} />
          <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(value) => [`${Math.round(Number(value))}%`, "Average capacity used"]} labelFormatter={(_, payload) => payload?.[0]?.payload?.label ?? ""} />
          <Bar dataKey="percentage" name="Average capacity used" className="fill-primary/60" radius={[4, 4, 0, 0]}>
            {view.rows.map((row) => <Cell key={row.startHour} className={row.isBusiest ? "fill-destructive" : row.isQuietest ? "fill-primary" : "fill-primary/60"} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
    <details className="mt-4 text-sm"><summary className="cursor-pointer font-semibold">Show values as a list</summary>
      <ul className="mt-3 grid gap-1">{view.rows.map((row) => <li className="flex justify-between gap-3 border-b border-border py-1" key={row.startHour}><span>{row.label}</span><strong>{formatPercentage(row.percentage)}</strong></li>)}</ul>
    </details>
  </>;
}

function WindowCard({ title, window }: { title: string; window: TrafficWindow | null }) {
  return <article className="rounded-xl bg-muted/50 p-4"><p className="text-xs font-black uppercase tracking-wider text-muted-foreground">{title}</p>{window ? <><p className="mt-2 text-lg font-bold">{window.label}</p><p className="text-sm text-muted-foreground">About {formatPercentage(window.average_capacity_percentage)} of capacity</p></> : <p className="mt-2 text-sm text-muted-foreground">Not available.</p>}</article>;
}
