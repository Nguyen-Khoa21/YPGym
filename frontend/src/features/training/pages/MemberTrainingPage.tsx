import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Dumbbell, Search } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest, apiUrl } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { MUSCLES, exerciseImage, type Exercise, type ExercisePage, type Muscle } from "@/features/training/types";

export function MemberTrainingPage() {
  const { id } = useParams();
  const { token } = useAuth();
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

  return <MemberShell><div className="mx-auto max-w-6xl">
    {id ? <>
      <Link to="/app/train" className="inline-flex items-center gap-2 text-sm font-bold text-primary"><ArrowLeft className="size-4" /> Exercise guide</Link>
      {detail.isLoading ? <LoadingState className="mt-5" title="Loading exercise" /> : null}
      {detail.isError ? <ErrorState className="mt-5" title={toUiError(detail.error).title} message={toUiError(detail.error).message} action={<Button variant="outline" onClick={() => detail.refetch()}>Retry</Button>} /> : null}
      {detail.data ? <article className="mt-6 overflow-hidden rounded-2xl border border-border bg-card">
        <ExerciseVisual item={detail.data} large />
        <div className="grid gap-6 p-6 sm:p-8"><div><p className="page-kicker">{detail.data.region} body · YPTrain</p><h1 className="page-title">{detail.data.name}</h1><p className="page-description">{detail.data.description}</p>{detail.data.is_illustrative ? <p className="mt-3 text-sm font-semibold text-muted-foreground">Illustrative guide. Confirm on-site equipment availability where applicable.</p> : null}</div>
          <section><h2 className="text-xl font-bold">How to use</h2><p className="mt-2 whitespace-pre-line text-muted-foreground">{detail.data.usage_steps}</p></section>
          <section><h2 className="text-xl font-bold">Muscles</h2><p className="mt-2"><strong>Primary:</strong> {detail.data.primary_muscles.join(", ")}</p><p><strong>Secondary:</strong> {detail.data.secondary_muscles.join(", ") || "None listed"}</p></section>
          <section className="rounded-xl bg-muted/60 p-4"><h2 className="font-bold">Safety note</h2><p className="mt-1 text-sm">{detail.data.safety_note}</p></section>
          <div><Button disabled>Add Exercise</Button><p className="mt-2 text-sm text-muted-foreground">Workout logging arrives in the next YPTrain update. A verified gym check-in will be required.</p></div>
        </div>
      </article> : null}
    </> : <>
      <p className="page-kicker">YPTrain · equipment guide</p><h1 className="page-title">Find your next exercise.</h1><p className="page-description">Browse the shared exercise catalogue by body region or muscle. Illustrative machine entries do not confirm what is installed at YPGym.</p>
      <div className="mt-7 grid gap-3 rounded-2xl border border-border bg-card p-4 sm:grid-cols-[1fr_auto]"><label className="flex h-11 items-center gap-2 rounded-md border border-input px-3"><Search className="size-4 text-muted-foreground" aria-hidden /><span className="sr-only">Search exercise name or muscle</span><input className="min-w-0 flex-1 bg-transparent text-sm outline-none" placeholder="Search name or muscle" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label><select aria-label="Filter by muscle" className="h-11 rounded-md border border-input bg-card px-3 text-sm" value={muscle} onChange={(event) => { setMuscle(event.target.value as Muscle | ""); setPage(1); }}><option value="">All muscles</option>{MUSCLES.map((value) => <option key={value} value={value}>{value}</option>)}</select></div>
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
  return <div className={`flex items-center justify-center bg-primary/10 ${large ? "h-64" : "h-36"}`}>{item.has_image ? <img className="h-full w-full object-cover" src={apiUrl(exerciseImage(item))} alt={`${item.name} exercise guide`} /> : <div className="flex items-center gap-2 text-primary"><Dumbbell className="size-12" aria-hidden /><span className="text-sm font-semibold">Image pending</span></div>}</div>;
}
