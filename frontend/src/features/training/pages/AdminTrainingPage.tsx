import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Pencil, Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { Modal, OperationsHeader, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { MUSCLES, type Exercise, type ExercisePage, type Muscle } from "@/features/training/types";
import { apiRequest, uploadApiImage } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { queryClient } from "@/lib/queryClient";

const schema = z.object({
  name: z.string().trim().min(2).max(160),
  description: z.string().trim().min(10).max(3000),
  region: z.enum(["upper", "lower"]),
  usage_steps: z.string().trim().min(10).max(4000),
  safety_note: z.string().trim().min(10).max(2000),
  primary_muscles: z.array(z.enum(MUSCLES)).min(1, "Select a primary muscle."),
  secondary_muscles: z.array(z.enum(MUSCLES)),
  is_illustrative: z.boolean(),
  is_active: z.boolean(),
}).refine((value) => !value.secondary_muscles.some((muscle) => value.primary_muscles.includes(muscle)), { path: ["secondary_muscles"], message: "Each muscle can have only one role." });
type Values = z.infer<typeof schema>;
const empty: Values = { name: "", description: "", region: "upper", usage_steps: "", safety_note: "", primary_muscles: [], secondary_muscles: [], is_illustrative: false, is_active: true };

export function AdminTrainingPage() {
  const { token } = useAuth();
  const [editing, setEditing] = useState<Exercise | "new" | null>(null);
  const [search, setSearch] = useState("");
  const [region, setRegion] = useState("");
  const [muscle, setMuscle] = useState<Muscle | "">("");
  const [page, setPage] = useState(1);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: empty });
  const params = new URLSearchParams({ page: String(page), page_size: "30" });
  if (search.trim()) params.set("search", search.trim());
  if (region) params.set("region", region);
  if (muscle) params.set("muscle", muscle);
  const list = useQuery({ queryKey: ["admin", "training", params.toString()], queryFn: ({ signal }) => apiRequest<ExercisePage>(`/admin/training/exercises?${params}`, { token, signal }) });
  const save = useMutation({ mutationFn: ({ id, values }: { id?: string; values: Values }) => apiRequest<Exercise>(id ? `/admin/training/exercises/${id}` : "/admin/training/exercises", { method: id ? "PATCH" : "POST", token, body: values }), onSuccess: async (item, variables) => { setEditing(null); form.reset(empty); await queryClient.invalidateQueries({ queryKey: ["admin", "training"] }); toast.success(variables.id ? "Exercise updated" : "Exercise created"); if (imageFile) { try { await uploadApiImage<Exercise>(`/admin/training/exercises/${item.id}/image`, imageFile, token); await queryClient.invalidateQueries({ queryKey: ["admin", "training"] }); toast.success("Image uploaded"); } catch (error) { toast.error(`Exercise saved, but image upload failed: ${toUiError(error).message}`); } } setImageFile(null); }, onError: (error) => toast.error(toUiError(error).message) });
  const toggle = useMutation({ mutationFn: (item: Exercise) => apiRequest<Exercise>(`/admin/training/exercises/${item.id}`, { method: "PATCH", token, body: { is_active: !item.is_active } }), onSuccess: async (item) => { await queryClient.invalidateQueries({ queryKey: ["admin", "training"] }); toast.success(item.is_active ? "Exercise restored" : "Exercise archived"); }, onError: (error) => toast.error(toUiError(error).message) });

  function open(item: Exercise | "new") {
    setEditing(item);
    setImageFile(null);
    form.reset(item === "new" ? empty : { name: item.name, description: item.description, region: item.region, usage_steps: item.usage_steps, safety_note: item.safety_note, primary_muscles: item.primary_muscles, secondary_muscles: item.secondary_muscles, is_illustrative: item.is_illustrative, is_active: item.is_active });
  }

  return <AdminShell><div className="mx-auto max-w-7xl">
    <OperationsHeader kicker="YPTrain catalogue" title="Manage the exercise guide." description="One catalogue powers member web and Expo. Illustrative machines are not a claim about installed equipment." actions={<Button onClick={() => open("new")}><Plus className="size-4" /> Add exercise</Button>} />
    <div className="mt-6 grid gap-3 rounded-xl border border-border bg-card p-4 sm:grid-cols-3"><label className="grid gap-1 text-sm font-bold">Search name or muscle<input className="h-11 rounded-md border border-input bg-card px-3 font-normal" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label><label className="grid gap-1 text-sm font-bold">Region<select className="h-11 rounded-md border border-input bg-card px-3 font-normal" value={region} onChange={(event) => { setRegion(event.target.value); setPage(1); }}><option value="">All regions</option><option value="upper">Upper</option><option value="lower">Lower</option></select></label><label className="grid gap-1 text-sm font-bold">Muscle<select className="h-11 rounded-md border border-input bg-card px-3 font-normal" value={muscle} onChange={(event) => { setMuscle(event.target.value as Muscle | ""); setPage(1); }}><option value="">All muscles</option>{MUSCLES.map((value) => <option key={value} value={value}>{value}</option>)}</select></label></div>
    {list.isLoading ? <LoadingState className="mt-5" title="Loading exercises" /> : null}
    {list.isError ? <ErrorState className="mt-5" title={toUiError(list.error).title} message={toUiError(list.error).message} action={<Button variant="outline" onClick={() => list.refetch()}>Retry</Button>} /> : null}
    {list.data?.items.length === 0 ? <EmptyState className="mt-5" title="No exercises match" message="Change the filters or add an exercise." action={<Button onClick={() => open("new")}>Add exercise</Button>} /> : null}
    <div className="mt-5 grid gap-4 md:grid-cols-2">{list.data?.items.map((item) => <article key={item.id} className="grid gap-3 rounded-xl border border-border bg-card p-5"><div className="flex items-start justify-between gap-3"><div><p className="page-kicker">{item.region} body</p><h2 className="text-xl font-bold">{item.name}</h2></div><StatusBadge value={item.is_active ? "active" : "inactive"} /></div><p className="text-sm text-muted-foreground">Primary: {item.primary_muscles.join(", ")}</p><p className="text-sm text-muted-foreground">{item.description}</p>{item.is_illustrative ? <p className="text-xs font-semibold text-muted-foreground">Illustrative entry · confirm equipment where applicable</p> : null}<div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => open(item)}><Pencil className="size-4" /> Edit / image</Button><Button variant={item.is_active ? "danger" : "outline"} disabled={toggle.isPending} onClick={() => { if (!item.is_active || window.confirm(`Archive ${item.name}? Members will no longer see it.`)) toggle.mutate(item); }}>{item.is_active ? "Archive" : "Restore"}</Button></div></article>)}</div>
    {list.data && list.data.page.pages > 1 ? <div className="mt-6 flex items-center gap-3"><Button variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button><span className="text-sm">Page {page} of {list.data.page.pages}</span><Button variant="outline" disabled={page >= list.data.page.pages} onClick={() => setPage(page + 1)}>Next</Button></div> : null}
    {editing ? <Modal title={editing === "new" ? "Add exercise" : `Edit ${editing.name}`} description="Usage and safety text appear in the member guide." error={save.isError ? toUiError(save.error).message : undefined} onClose={() => setEditing(null)}><form className="ops-modal__body" onSubmit={form.handleSubmit((values) => save.mutate({ id: editing === "new" ? undefined : editing.id, values }))}><div className="grid gap-4">
      <label className="grid gap-1 text-sm font-bold">Name<input className="h-11 rounded-md border border-input px-3 font-normal" {...form.register("name")} />{form.formState.errors.name ? <span className="text-xs text-destructive">{form.formState.errors.name.message}</span> : null}</label>
      <label className="grid gap-1 text-sm font-bold">Region<select className="h-11 rounded-md border border-input px-3 font-normal" {...form.register("region")}><option value="upper">Upper body</option><option value="lower">Lower body</option></select></label>
      {(["description", "usage_steps", "safety_note"] as const).map((key) => <label key={key} className="grid gap-1 text-sm font-bold capitalize">{key.replace("_", " ")}<textarea className="min-h-24 rounded-md border border-input p-3 font-normal" {...form.register(key)} />{form.formState.errors[key] ? <span className="text-xs text-destructive">{form.formState.errors[key]?.message}</span> : null}</label>)}
      {(["primary_muscles", "secondary_muscles"] as const).map((key) => <fieldset key={key} className="rounded-lg border border-border p-3"><legend className="px-1 text-sm font-bold capitalize">{key.replace("_", " ")}</legend><div className="grid grid-cols-2 gap-2 sm:grid-cols-3">{MUSCLES.map((muscle) => <label key={muscle} className="flex min-h-9 items-center gap-2 text-sm"><input type="checkbox" value={muscle} {...form.register(key)} />{muscle}</label>)}</div>{form.formState.errors[key] ? <p className="text-xs text-destructive">{form.formState.errors[key]?.message}</p> : null}</fieldset>)}
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...form.register("is_illustrative")} />Illustrative entry (equipment availability unconfirmed)</label>
      {editing !== "new" ? <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...form.register("is_active")} />Visible to members</label> : null}
      <label className="grid gap-1 text-sm font-bold">Exercise image <span className="font-normal text-muted-foreground">PNG, JPEG or WebP, under 2 MB and 4 megapixels. Saved as a sanitized JPEG.</span><input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => { const file = event.target.files?.[0] ?? null; if (file && file.size > 2_000_000) { toast.error("Choose an image smaller than 2 MB."); event.target.value = ""; setImageFile(null); } else setImageFile(file); }} /></label>
    </div><div className="ops-modal__actions"><Button type="button" variant="outline" onClick={() => setEditing(null)}>Cancel</Button><Button type="submit" disabled={save.isPending}>{save.isPending ? "Saving..." : "Save exercise"}</Button></div></form></Modal> : null}
  </div></AdminShell>;
}
