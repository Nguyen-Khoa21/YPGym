import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Pencil, Plus, UserRoundX } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { Modal, OperationsHeader, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { PTCard } from "@/features/classes/components/PTCard";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { queryClient } from "@/lib/queryClient";
import type { Trainer } from "@/types/operations";

const trainerSchema = z.object({
  display_name: z.string().min(2, "Use at least 2 characters.").max(160),
  specialty: z.string().max(180).optional(),
  availability_summary: z.string().max(500).optional(),
  bio: z.string().max(3000).optional(),
});
type TrainerForm = z.infer<typeof trainerSchema>;
const emptyTrainer: TrainerForm = { display_name: "", specialty: "", availability_summary: "", bio: "" };

export function AdminTrainersPage() {
  const { token } = useAuth();
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState<Trainer | "new" | null>(null);
  const [deactivating, setDeactivating] = useState<Trainer | null>(null);
  const query = useQuery({ queryKey: ["admin", "trainers", filter], queryFn: ({ signal }) => apiRequest<Trainer[]>(`/admin/trainers${filter ? `?active=${filter}` : ""}`, { token, signal }) });
  const form = useForm<TrainerForm>({ resolver: zodResolver(trainerSchema), defaultValues: emptyTrainer });
  const save = useMutation({
    mutationFn: ({ id, values }: { id?: string; values: TrainerForm }) => apiRequest<Trainer>(id ? `/admin/trainers/${id}` : "/admin/trainers", { method: id ? "PATCH" : "POST", token, body: { display_name: values.display_name, specialty: values.specialty || null, availability_summary: values.availability_summary || null, bio: values.bio || null } }),
    onSuccess: async (_, variables) => { setEditing(null); form.reset(emptyTrainer); await Promise.all([queryClient.invalidateQueries({ queryKey: ["admin", "trainers"] }), queryClient.invalidateQueries({ queryKey: ["admin", "class-trainers"] }), queryClient.invalidateQueries({ queryKey: ["trainers"] })]); toast.success(variables.id ? "Trainer updated" : "Trainer created"); },
    onError: (error) => toast.error(toUiError(error).message),
  });
  const deactivate = useMutation({
    mutationFn: (id: string) => apiRequest<Trainer>(`/admin/trainers/${id}/deactivate`, { method: "POST", token }),
    onSuccess: async () => { setDeactivating(null); await Promise.all([queryClient.invalidateQueries({ queryKey: ["admin", "trainers"] }), queryClient.invalidateQueries({ queryKey: ["admin", "class-trainers"] }), queryClient.invalidateQueries({ queryKey: ["trainers"] })]); toast.success("Trainer deactivated"); },
    onError: (error) => toast.error(toUiError(error).message),
  });

  function openNew() { save.reset(); form.reset(emptyTrainer); setEditing("new"); }
  function openEdit(trainer: Trainer) { save.reset(); form.reset({ display_name: trainer.display_name, specialty: trainer.specialty ?? "", availability_summary: trainer.availability_summary ?? "", bio: trainer.bio ?? "" }); setEditing(trainer); }

  return <AdminShell><div className="mx-auto max-w-7xl">
    <OperationsHeader kicker="PT profile management" title="Keep coaches current." description="Maintain member-safe trainer profiles and their upcoming class summaries without creating a second trainer identity." actions={<Button onClick={openNew}><Plus className="size-4" /> Add trainer</Button>} />
    <div className="mt-7 flex flex-wrap items-center gap-3"><label className="text-sm font-bold" htmlFor="trainer-status">Profile status</label><select id="trainer-status" className="h-11 rounded-md border border-input bg-card px-3 text-sm" value={filter} onChange={(event) => setFilter(event.target.value)}><option value="">All trainers</option><option value="true">Active</option><option value="false">Inactive</option></select></div>
    {query.isLoading ? <LoadingState className="mt-5" title="Loading trainer profiles" /> : null}
    {query.isError ? <ErrorState className="mt-5" title={toUiError(query.error).title} message={toUiError(query.error).message} action={<Button variant="outline" onClick={() => query.refetch()}>Retry</Button>} /> : null}
    {query.data?.length === 0 ? <EmptyState className="mt-5" title="No trainer profiles" message="Change the status filter or add the first trainer profile." action={<Button onClick={openNew}>Add trainer</Button>} /> : null}
    {query.data?.length ? <section className="mt-5 grid gap-4 lg:grid-cols-2">{query.data.map((trainer) => <div className="grid content-start gap-3" key={trainer.id}><PTCard trainer={trainer} /><div className="flex items-center justify-between rounded-xl border border-border bg-card px-4 py-3"><StatusBadge value={trainer.is_active ? "active" : "inactive"} /><div className="flex gap-2"><Button variant="outline" onClick={() => openEdit(trainer)}><Pencil className="size-4" /> Edit</Button>{trainer.is_active ? <Button variant="danger" onClick={() => { deactivate.reset(); setDeactivating(trainer); }}><UserRoundX className="size-4" /> Deactivate</Button> : null}</div></div></div>)}</section> : null}
    {editing ? <Modal error={(save).isError ? toUiError((save).error).message : undefined} title={editing === "new" ? "Add trainer profile" : `Edit ${editing.display_name}`} description="Only member-safe profile details are displayed outside the management route." onClose={() => setEditing(null)}><form className="ops-modal__body" onSubmit={form.handleSubmit((values) => save.mutate({ id: editing === "new" ? undefined : editing.id, values }))}><div className="grid gap-4"><Field><Label htmlFor="trainer-display_name">Name</Label><Input id="trainer-display_name" {...form.register("display_name")} /><FieldError message={form.formState.errors.display_name?.message} /></Field><Field><Label htmlFor="trainer-specialty">Specialty</Label><Input id="trainer-specialty" {...form.register("specialty")} /><FieldError message={form.formState.errors.specialty?.message} /></Field><Field><Label htmlFor="trainer-availability_summary">Availability summary</Label><Input id="trainer-availability_summary" {...form.register("availability_summary")} /><FieldError message={form.formState.errors.availability_summary?.message} /></Field><Field><Label htmlFor="trainer-bio">Short bio</Label><textarea id="trainer-bio" className="w-full min-h-28 rounded-md border border-input p-3 text-sm" {...form.register("bio")} /><FieldError message={form.formState.errors.bio?.message} /></Field></div><div className="ops-modal__actions"><Button type="button" variant="outline" onClick={() => setEditing(null)}>Cancel</Button><Button type="submit" disabled={save.isPending}>{editing === "new" ? "Create profile" : "Save changes"}</Button></div></form></Modal> : null}
    {deactivating ? <Modal error={(deactivate).isError ? toUiError((deactivate).error).message : undefined} title={`Deactivate ${deactivating.display_name}?`} description="Historical assignments stay intact. Deactivation is blocked until all scheduled future classes are reassigned or unassigned." onClose={() => setDeactivating(null)}><div className="ops-modal__body"><div className="ops-modal__actions"><Button variant="outline" onClick={() => setDeactivating(null)}>Keep active</Button><Button variant="danger" disabled={deactivate.isPending} onClick={() => deactivate.mutate(deactivating.id)}>Confirm deactivation</Button></div></div></Modal> : null}
  </div></AdminShell>;
}
