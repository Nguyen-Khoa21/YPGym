import { useRef, useState } from "react";
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { ArrowLeft, Dumbbell, Search } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { TrainingHistory } from "@/features/training/components/TrainingHistory";
import { apiRequest, apiUrl } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { MUSCLES, MUSCLE_LABELS, exerciseImage, type Exercise, type ExerciseHistoryPage, type ExercisePage, type Muscle, type WorkoutToday } from "@/features/training/types";

export function MemberTrainingPage() {
  const { id } = useParams();
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [region, setRegion] = useState<"all" | "upper" | "lower">("all");
  const [search, setSearch] = useState("");
  const [muscle, setMuscle] = useState<Muscle | "">("");
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page: String(page), page_size: "30" });
  if (region !== "all") params.set("region", region);
  if (search.trim()) params.set("search", search.trim());
  if (muscle) params.set("muscle", muscle);
  const list = useQuery({ queryKey: ["training", "exercises", params.toString()], queryFn: ({ signal }) => apiRequest<ExercisePage>(`/training/exercises?${params}`, { token, signal }), enabled: !id });
  const detail = useQuery({ queryKey: ["training", "exercise", id], queryFn: ({ signal }) => apiRequest<Exercise>(`/training/exercises/${id}`, { token, signal }), enabled: !!id });
  const exerciseHistory = useQuery({ queryKey: ["training", "exercise-history", id], queryFn: ({ signal }) => apiRequest<ExerciseHistoryPage>(`/training/exercises/${id}/history?page_size=10`, { token, signal }), enabled: !!id });
  const today = useQuery({ queryKey: ["training", "workout", "today"], queryFn: ({ signal }) => apiRequest<WorkoutToday>("/training/workouts/today", { token, signal }) });
  const saved = (value: WorkoutToday) => { queryClient.setQueryData(["training", "workout", "today"], value); void Promise.all([queryClient.invalidateQueries({ queryKey: ["training", "history"] }), queryClient.invalidateQueries({ queryKey: ["training", "muscle-map"] }), queryClient.invalidateQueries({ queryKey: ["training", "exercise-history", id] })]); };

  return <MemberShell><div className="mx-auto max-w-6xl">
    {id ? <>
      <Link to="/app/train" className="inline-flex items-center gap-2 text-sm font-bold text-primary"><ArrowLeft className="size-4" /> Exercise guide</Link>
      {detail.isLoading ? <LoadingState className="mt-5" title="Loading exercise" /> : null}
      {detail.isError ? <ErrorState className="mt-5" title={toUiError(detail.error).title} message={toUiError(detail.error).message} action={<Button variant="outline" onClick={() => detail.refetch()}>Retry</Button>} /> : null}
      {detail.data ? <article className="mt-6 overflow-hidden rounded-2xl border border-border bg-card">
        <ExerciseVisual item={detail.data} large />
        <div className="grid gap-6 p-6 sm:p-8"><div><p className="page-kicker">{detail.data.region} body · YPTrain</p><h1 className="page-title">{detail.data.name}</h1><p className="page-description">{detail.data.description}</p>{detail.data.is_illustrative ? <p className="mt-3 text-sm font-semibold text-muted-foreground">Illustrative guide. Confirm on-site equipment availability where applicable.</p> : null}</div>
          <section><h2 className="text-xl font-bold">How to use</h2><p className="mt-2 whitespace-pre-line text-muted-foreground">{detail.data.usage_steps}</p></section>
          <section><h2 className="text-xl font-bold">Muscles</h2><p className="mt-2"><strong>Primary:</strong> {detail.data.primary_muscles.map((value) => MUSCLE_LABELS[value]).join(", ")}</p><p><strong>Secondary:</strong> {detail.data.secondary_muscles.map((value) => MUSCLE_LABELS[value]).join(", ") || "None listed"}</p></section>
          <section className="rounded-xl bg-muted/60 p-4"><h2 className="font-bold">Safety note</h2><p className="mt-1 text-sm">{detail.data.safety_note}</p></section>
          <div><h2 className="text-xl font-bold">Add Exercise</h2>{today.isLoading ? <LoadingState title="Checking today's gym visit" /> : null}{today.isError ? <ErrorState title="Workout unavailable" message={toUiError(today.error).message} action={<Button variant="outline" onClick={() => today.refetch()}>Retry</Button>} /> : null}{today.data?.eligible ? <WorkoutForm key={detail.data.id} exercise={detail.data} token={token} onSaved={saved} /> : today.data ? <p className="mt-2 text-sm text-muted-foreground">{today.data.reason} <Button variant="outline" onClick={() => today.refetch()}>Check again</Button></p> : null}</div>
        </div>
      </article> : null}
      {today.data?.session ? <WorkoutSummary value={today.data} /> : null}
      <ExerciseHistory query={exerciseHistory} />
    </> : <>
      <p className="page-kicker">YPTrain · equipment guide</p><h1 className="page-title">Find your next exercise.</h1><p className="page-description">Browse the shared exercise catalogue by body region or muscle. Illustrative machine entries do not confirm what is installed at YPGym.</p>
      {today.data?.session ? <WorkoutSummary value={today.data} /> : today.data ? <p className="mt-5 rounded-xl border border-border bg-card p-4 text-sm">{today.data.eligible ? "Your gym check-in is confirmed. Open an exercise to start today's workout." : today.data.reason}</p> : null}
      <TrainingHistory token={token} />
      <div className="mt-7 grid gap-3 rounded-2xl border border-border bg-card p-4 sm:grid-cols-[1fr_auto]"><label className="flex h-11 items-center gap-2 rounded-md border border-input px-3"><Search className="size-4 text-muted-foreground" aria-hidden /><span className="sr-only">Search exercise name or muscle</span><input className="min-w-0 flex-1 bg-transparent text-sm outline-none" placeholder="Search name or muscle" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label><select aria-label="Filter by muscle" className="h-11 rounded-md border border-input bg-card px-3 text-sm" value={muscle} onChange={(event) => { setMuscle(event.target.value as Muscle | ""); setPage(1); }}><option value="">All muscles</option>{MUSCLES.map((value) => <option key={value} value={value}>{MUSCLE_LABELS[value]}</option>)}</select></div>
      <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Body region">{(["all", "upper", "lower"] as const).map((value) => <Button key={value} variant={region === value ? "primary" : "outline"} onClick={() => { setRegion(value); setPage(1); }}>{value === "all" ? "All exercises" : `${value} body`}</Button>)}</div>
      {list.isLoading ? <LoadingState className="mt-5" title="Loading exercises" /> : null}
      {list.isError ? <ErrorState className="mt-5" title={toUiError(list.error).title} message={toUiError(list.error).message} action={<Button variant="outline" onClick={() => list.refetch()}>Retry</Button>} /> : null}
      {list.data?.items.length === 0 ? <EmptyState className="mt-5" title="No exercises match" message="Try a different name, region or muscle." /> : null}
      {(["upper", "lower"] as const).map((section) => { const items = list.data?.items.filter((item) => item.region === section) ?? []; return items.length ? <section key={section} className="mt-7"><h2 className="text-2xl font-bold capitalize">{section} body</h2><div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{items.map((item) => <Link key={item.id} to={`/app/train/${item.id}`} className="overflow-hidden rounded-2xl border border-border bg-card transition hover:border-primary focus-visible:outline-2 focus-visible:outline-primary"><ExerciseVisual item={item} /><div className="p-4"><h3 className="text-xl font-bold">{item.name}</h3><p className="mt-1 text-sm text-muted-foreground">Primary: {item.primary_muscles.join(", ")}</p>{item.is_illustrative ? <p className="mt-2 text-xs font-semibold text-muted-foreground">Illustrative</p> : null}</div></Link>)}</div></section> : null; })}
      {list.data && list.data.page.pages > 1 ? <div className="mt-6 flex items-center gap-3"><Button variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button><span className="text-sm">Page {page} of {list.data.page.pages}</span><Button variant="outline" disabled={page >= list.data.page.pages} onClick={() => setPage(page + 1)}>Next</Button></div> : null}
    </>}
  </div></MemberShell>;
}

function ExerciseVisual({ item, large = false }: { item: Exercise; large?: boolean }) {
  return <div className={`flex w-full items-center justify-center bg-primary/10 ${large ? "aspect-[800/448] max-h-[448px]" : "h-36"}`}>{item.has_image ? <img className={large ? "max-h-[448px] w-full object-contain" : "h-full w-full object-cover"} src={apiUrl(exerciseImage(item))} alt={`${item.name} exercise guide`} /> : <div className="flex items-center gap-2 text-primary"><Dumbbell className="size-12" aria-hidden /><span className="text-sm font-semibold">Image pending</span></div>}</div>;
}

type SetDraft = { reps: string; weight: string; unit: "kg" | "lb" };
const blankSet = (): SetDraft => ({ reps: "", weight: "0", unit: "kg" });

function WorkoutForm({ exercise, token, onSaved }: { exercise: Exercise; token: string | null; onSaved: (value: WorkoutToday) => void }) {
  const [count, setCount] = useState(1);
  const [rows, setRows] = useState<SetDraft[]>(() => Array.from({ length: 10 }, blankSet));
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const submitting = useRef(false);
  const change = (index: number, patch: Partial<SetDraft>) => { setRows((previous) => previous.map((row, i) => i === index ? { ...row, ...patch } : row)); setKey(crypto.randomUUID()); setError(""); setSaved(false); };
  const changeCount = (next: number) => { setCount(next); setKey(crypto.randomUUID()); setSaved(false); setError(""); };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (submitting.current) return;
    const sets = rows.slice(0, count);
    if (sets.some((row) => !Number.isInteger(Number(row.reps)) || Number(row.reps) < 1 || Number(row.reps) > 1000 || !/^\d+(\.\d{1,2})?$/.test(row.weight) || Number(row.weight) > 9999.99)) { setError("Enter 1–1000 whole reps and a non-negative weight up to 9999.99 for every set."); return; }
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<WorkoutToday>("/training/workouts/today/exercises", { method: "POST", token, body: { exercise_id: exercise.id, idempotency_key: key, sets: sets.map((row) => ({ reps: Number(row.reps), weight: row.weight, unit: row.unit })) } });
      onSaved(result);
      setSaved(true);
      setKey(crypto.randomUUID());
      setRows(Array.from({ length: 10 }, blankSet));
      setCount(1);
    } catch (cause) { setError(toUiError(cause).message); }
    finally { submitting.current = false; setBusy(false); }
  };
  return <form onSubmit={submit} className="mt-4 space-y-4"><p className="text-sm text-muted-foreground">Log external load in kg or lb. Use 0 kg for bodyweight or no added load; it does not mean zero effort.</p>
    <div className="flex items-center gap-3"><span className="font-semibold">Sets</span><Button type="button" variant="outline" disabled={busy || count <= 1} aria-label="Remove one set" onClick={() => changeCount(count - 1)}>−</Button><output aria-live="polite">{count}</output><Button type="button" variant="outline" disabled={busy || count >= 10} aria-label="Add one set" onClick={() => changeCount(count + 1)}>+</Button></div>
    {rows.slice(0, count).map((row, index) => <div key={index} className="grid gap-3 rounded-xl border border-border p-3 sm:grid-cols-[auto_1fr_1fr_100px] sm:items-end"><strong>Set {index + 1}</strong><label className="grid gap-1 text-sm">Reps<input required type="number" min="1" max="1000" step="1" value={row.reps} disabled={busy} onChange={(event) => change(index, { reps: event.target.value })} className="h-11 rounded-md border border-input bg-card px-3" /></label><label className="grid gap-1 text-sm">External weight<input required type="number" min="0" max="9999.99" step="0.01" value={row.weight} disabled={busy} onChange={(event) => change(index, { weight: event.target.value })} className="h-11 rounded-md border border-input bg-card px-3" /></label><label className="grid gap-1 text-sm">Unit<select value={row.unit} disabled={busy} onChange={(event) => change(index, { unit: event.target.value as "kg" | "lb" })} className="h-11 rounded-md border border-input bg-card px-3"><option value="kg">kg</option><option value="lb">lb</option></select></label></div>)}
    {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}{saved ? <p role="status" className="text-sm font-semibold text-primary">Exercise saved to today's workout.</p> : null}<Button type="submit" disabled={busy}>{busy ? "Saving…" : "Save exercise"}</Button>
  </form>;
}

function WorkoutSummary({ value }: { value: WorkoutToday }) {
  if (!value.session) return null;
  return <section className="mt-6 rounded-2xl border border-border bg-card p-5" aria-label="Today's workout"><p className="page-kicker">{value.gym_date} · {value.gym_timezone}</p><h2 className="text-xl font-bold">Today's workout</h2>{value.session.exercises.map((exercise) => <div key={exercise.id} className="mt-4 border-t border-border pt-3"><h3 className="font-semibold">{exercise.name}</h3><p className="text-sm text-muted-foreground">{exercise.sets.map((set) => `${set.set_order}: ${set.reps} reps × ${set.weight} ${set.unit}`).join(" · ")}</p></div>)}</section>;
}

function ExerciseHistory({ query }: { query: UseQueryResult<ExerciseHistoryPage> }) {
  return <section className="mt-6 rounded-2xl border border-border bg-card p-5" aria-labelledby="exercise-history-title"><h2 id="exercise-history-title" className="text-xl font-bold">Your prior sessions</h2><p className="mt-1 text-sm text-muted-foreground">Descriptive comparisons use your previous logged session for this exercise. They are not a next-session target.</p>
    {query.isLoading ? <LoadingState className="mt-4" title="Loading prior sessions" /> : null}
    {query.isError ? <ErrorState className="mt-4" title="Prior sessions unavailable" message={toUiError(query.error).message} action={<Button variant="outline" onClick={() => query.refetch()}>Retry</Button>} /> : null}
    {query.data?.items.length === 0 ? <EmptyState className="mt-4" title="No prior sessions" message="Your logged sessions for this exercise will appear here." /> : null}
    {query.data?.items.map((item) => <article key={item.workout_exercise_id} className="mt-4 rounded-xl border border-border p-4"><div className="flex flex-wrap items-center justify-between gap-2"><strong>{item.workout_date}</strong>{item.comparison_to_previous ? <span className="text-xs font-semibold text-muted-foreground">Sets {item.comparison_to_previous.sets} · reps {item.comparison_to_previous.reps} · load {item.comparison_to_previous.external_load}</span> : <span className="text-xs text-muted-foreground">First recorded baseline</span>}</div><p className="mt-2 text-sm">{item.set_count} sets · {item.total_reps} total reps · {item.max_external_load_kg} kg max external load</p><p className="mt-1 text-sm text-muted-foreground">{item.sets.map((set) => `${set.set_order}: ${set.reps} reps × ${set.weight} ${set.unit}`).join(" · ")}</p></article>)}
  </section>;
}
