import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { Button } from "@/components/ui/Button";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { type Muscle, type WorkoutDayDetail, type WorkoutHistoryDay, type WorkoutHistoryPage, type WorkoutWeekSummary } from "@/features/training/types";

const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const intensityClass = ["bg-muted text-foreground", "bg-red-100 text-red-950", "bg-red-300 text-red-950", "bg-red-500 text-white", "bg-red-700 text-white"];
const intensityLabel = ["No workout", "Light", "Moderate", "High", "Highest"];
const muscleColor = ["#E5E7EB", "#FEE2E2", "#FCA5A5", "#F87171", "#B91C1C"];

export function TrainingHistory({ token }: { token: string | null }) {
  const [month, setMonth] = useState(() => monthKey(new Date()));
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const monthInfo = useMemo(() => getMonth(month), [month]);
  const history = useQuery({
    queryKey: ["training", "history", month],
    queryFn: ({ signal }) => apiRequest<WorkoutHistoryPage>(`/training/workouts/history?date_from=${monthInfo.first}&date_to=${monthInfo.last}&page_size=100`, { token, signal }),
  });
  const week = useQuery({ queryKey: ["training", "muscle-map", "current"], queryFn: ({ signal }) => apiRequest<WorkoutWeekSummary>("/training/workouts/muscle-map", { token, signal }) });
  const detail = useQuery({
    queryKey: ["training", "workout", selectedDate],
    queryFn: ({ signal }) => apiRequest<WorkoutDayDetail>(`/training/workouts/${selectedDate}`, { token, signal }),
    enabled: !!selectedDate,
  });
  const activity = new Map(history.data?.items.map((item) => [item.workout_date, item]));

  const moveMonth = (offset: number) => {
    const [year, value] = month.split("-").map(Number);
    setMonth(monthKey(new Date(year, value - 1 + offset, 1)));
    setSelectedDate(null);
  };

  return <div className="mt-8 grid gap-6">
    <section className="rounded-2xl border border-border bg-card p-5 sm:p-6" aria-labelledby="workout-history-title">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="page-kicker">Attendance and workouts</p><h2 id="workout-history-title" className="text-2xl font-bold">Workout calendar</h2></div><div className="flex items-center gap-2"><Button variant="outline" aria-label="Previous month" onClick={() => moveMonth(-1)}><ChevronLeft className="size-4" /></Button><strong className="min-w-32 text-center">{monthInfo.label}</strong><Button variant="outline" aria-label="Next month" onClick={() => moveMonth(1)}><ChevronRight className="size-4" /></Button></div></div>
      <p className="mt-2 text-sm text-muted-foreground">Outlined dates are attended days. Red shades show relative weighted set exposure for logged workouts in this month.</p>
      {history.isLoading ? <LoadingState className="mt-4" title="Loading workout history" /> : null}
      {history.isError ? <ErrorState className="mt-4" title="History unavailable" message={toUiError(history.error).message} action={<Button variant="outline" onClick={() => history.refetch()}>Retry</Button>} /> : null}
      {history.data ? <>
        <div className="mt-5 grid grid-cols-7 gap-2" role="grid" aria-label={`${monthInfo.label} workout calendar`}>
          {dayNames.map((name) => <div key={name} role="columnheader" className="pb-1 text-center text-xs font-bold text-muted-foreground">{name}</div>)}
          {Array.from({ length: monthInfo.offset }, (_, index) => <span key={`blank-${index}`} aria-hidden />)}
          {Array.from({ length: monthInfo.days }, (_, index) => {
            const day = index + 1;
            const iso = `${month}-${String(day).padStart(2, "0")}`;
            const item = activity.get(iso);
            return <CalendarDay key={iso} day={day} item={item} selected={selectedDate === iso} onSelect={() => setSelectedDate(iso)} />;
          })}
        </div>
        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-muted-foreground" aria-label="Calendar intensity legend">{intensityLabel.map((label, level) => <span key={label} className="inline-flex items-center gap-1.5"><span className={`size-4 rounded ${intensityClass[level]}`} aria-hidden />{label}</span>)}<span className="inline-flex items-center gap-1.5"><span className="size-4 rounded border-2 border-primary" aria-hidden />Attended</span></div>
        {history.data.items.length === 0 ? <EmptyState className="mt-4" title="No activity this month" message="Scanner attendance and logged workouts will appear here." /> : null}
      </> : null}
      {selectedDate && detail.isLoading ? <LoadingState className="mt-4" title="Loading selected day" /> : null}
      {selectedDate && detail.isError ? <ErrorState className="mt-4" title="Day unavailable" message={toUiError(detail.error).message} action={<Button variant="outline" onClick={() => detail.refetch()}>Retry</Button>} /> : null}
      {detail.data ? <DayDetail value={detail.data} /> : null}
    </section>

    <section className="rounded-2xl border border-border bg-card p-5 sm:p-6" aria-labelledby="muscle-map-title">
      <p className="page-kicker">Current Monday–Sunday week</p><h2 id="muscle-map-title" className="text-2xl font-bold">Weekly muscle map</h2>
      {week.isLoading ? <LoadingState className="mt-4" title="Calculating weekly exposure" /> : null}
      {week.isError ? <ErrorState className="mt-4" title="Muscle map unavailable" message={toUiError(week.error).message} action={<Button variant="outline" onClick={() => week.refetch()}>Retry</Button>} /> : null}
      {week.data ? <MuscleMap value={week.data} /> : null}
    </section>
  </div>;
}

function CalendarDay({ day, item, selected, onSelect }: { day: number; item?: WorkoutHistoryDay; selected: boolean; onSelect: () => void }) {
  const label = item ? `${item.workout_date}: ${item.attended ? "attended" : "not attended"}; ${item.has_workout ? `${item.set_count} sets, ${item.exposure_score} weighted set exposure, ${intensityLabel[item.intensity_level]} intensity` : "no workout logged"}` : `${day}: no activity`;
  return <button type="button" role="gridcell" disabled={!item} aria-label={label} aria-pressed={selected} onClick={onSelect} className={`relative grid aspect-square min-h-10 place-items-center rounded-lg border text-sm font-bold transition focus-visible:outline-2 focus-visible:outline-primary ${item?.has_workout ? intensityClass[item.intensity_level] : "bg-card"} ${item?.attended ? "border-2 border-primary" : "border-border"} ${selected ? "ring-2 ring-secondary ring-offset-2" : ""} disabled:cursor-default disabled:opacity-55`}>{day}{item?.has_workout ? <span className="absolute bottom-0.5 text-[8px] font-black" aria-hidden>{item.set_count} sets</span> : null}</button>;
}

function DayDetail({ value }: { value: WorkoutDayDetail }) {
  return <article className="mt-5 rounded-xl border border-border bg-muted/40 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-lg font-bold">{formatIsoDate(value.workout_date)}</h3><span className="text-xs font-bold text-primary">{value.attended ? "Gym attendance recorded" : "Workout only"}</span></div><p className="mt-1 text-sm text-muted-foreground">{value.exposure_score} weighted set exposure</p>{value.session ? value.session.exercises.map((exercise) => <div key={exercise.id} className="mt-4 border-t border-border pt-3"><strong>{exercise.name}</strong><p className="mt-1 text-sm text-muted-foreground">{exercise.sets.map((set) => `${set.set_order}: ${set.reps} reps × ${set.weight} ${set.unit}`).join(" · ")}</p></div>) : <p className="mt-3 text-sm">You attended the gym but did not log a workout.</p>}</article>;
}

function MuscleMap({ value }: { value: WorkoutWeekSummary }) {
  const scores = Object.fromEntries(value.muscles.map((item) => [item.muscle, item.intensity_level])) as Record<Muscle, 0 | 1 | 2 | 3 | 4>;
  return <div className="mt-5"><p className="text-sm text-muted-foreground">{formatIsoDate(value.week_start)}–{formatIsoDate(value.week_end)} · {value.total_exposure_score} total exposure</p><p className="mt-2 text-sm">{value.metric.description} {value.metric.bodyweight_handling}</p><div className="mt-5 grid gap-6 lg:grid-cols-[minmax(280px,0.8fr)_1.2fr]"><div className="grid grid-cols-2 gap-3 rounded-xl bg-muted/40 p-3"><BodyFigure side="Front" scores={scores} /><BodyFigure side="Back" scores={scores} /></div><div><h3 className="font-bold">Muscle-by-muscle exposure</h3><ul className="mt-3 grid gap-2 sm:grid-cols-2">{value.muscles.map((item) => <li key={item.muscle} className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-sm"><span className="capitalize">{item.muscle}</span><span className="font-semibold">{item.exposure_score} · {intensityLabel[item.intensity_level]}</span></li>)}</ul></div></div><p className="mt-4 text-xs text-muted-foreground">This diagram summarizes logged set exposure. It does not measure anatomical activation or provide a training prescription.</p></div>;
}

function BodyFigure({ side, scores }: { side: "Front" | "Back"; scores: Record<Muscle, 0 | 1 | 2 | 3 | 4> }) {
  const fill = (muscle: Muscle) => muscleColor[scores[muscle] ?? 0];
  return <figure className="text-center"><svg viewBox="0 0 140 300" className="mx-auto h-64 w-full max-w-36" aria-hidden><circle cx="70" cy="24" r="18" fill="#D1D5DB" /><rect x="50" y="44" width="40" height="94" rx="18" fill="#E5E7EB" /><rect x="34" y="52" width="16" height="105" rx="8" fill="#E5E7EB" /><rect x="90" y="52" width="16" height="105" rx="8" fill="#E5E7EB" /><rect x="51" y="135" width="18" height="140" rx="9" fill="#E5E7EB" /><rect x="71" y="135" width="18" height="140" rx="9" fill="#E5E7EB" />{side === "Front" ? <>
        <circle cx="49" cy="58" r="10" fill={fill("shoulders")} /><circle cx="91" cy="58" r="10" fill={fill("shoulders")} /><rect x="54" y="57" width="32" height="26" rx="8" fill={fill("chest")} /><rect x="36" y="68" width="12" height="34" rx="6" fill={fill("biceps")} /><rect x="92" y="68" width="12" height="34" rx="6" fill={fill("biceps")} /><rect x="35" y="105" width="11" height="43" rx="5" fill={fill("forearms")} /><rect x="94" y="105" width="11" height="43" rx="5" fill={fill("forearms")} /><rect x="58" y="86" width="24" height="43" rx="7" fill={fill("core")} /><rect x="53" y="143" width="15" height="64" rx="7" fill={fill("quadriceps")} /><rect x="72" y="143" width="15" height="64" rx="7" fill={fill("quadriceps")} /><rect x="54" y="215" width="13" height="50" rx="6" fill={fill("calves")} /><rect x="73" y="215" width="13" height="50" rx="6" fill={fill("calves")} />
      </> : <>
        <circle cx="49" cy="58" r="10" fill={fill("shoulders")} /><circle cx="91" cy="58" r="10" fill={fill("shoulders")} /><path d="M54 61 Q70 50 86 61 L82 112 Q70 128 58 112 Z" fill={fill("back")} /><rect x="36" y="70" width="12" height="34" rx="6" fill={fill("triceps")} /><rect x="92" y="70" width="12" height="34" rx="6" fill={fill("triceps")} /><rect x="35" y="107" width="11" height="41" rx="5" fill={fill("forearms")} /><rect x="94" y="107" width="11" height="41" rx="5" fill={fill("forearms")} /><ellipse cx="61" cy="145" rx="10" ry="13" fill={fill("glutes")} /><ellipse cx="79" cy="145" rx="10" ry="13" fill={fill("glutes")} /><rect x="53" y="158" width="15" height="51" rx="7" fill={fill("hamstrings")} /><rect x="72" y="158" width="15" height="51" rx="7" fill={fill("hamstrings")} /><rect x="54" y="215" width="13" height="50" rx="6" fill={fill("calves")} /><rect x="73" y="215" width="13" height="50" rx="6" fill={fill("calves")} />
      </>}</svg><figcaption className="text-sm font-bold">{side}</figcaption></figure>;
}

function monthKey(value: Date) { return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`; }
function getMonth(value: string) { const [year, month] = value.split("-").map(Number); const days = new Date(year, month, 0).getDate(); return { first: `${value}-01`, last: `${value}-${String(days).padStart(2, "0")}`, days, offset: (new Date(year, month - 1, 1).getDay() + 6) % 7, label: new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" }).format(new Date(year, month - 1, 1)) }; }
function formatIsoDate(value: string) { return new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`)); }
