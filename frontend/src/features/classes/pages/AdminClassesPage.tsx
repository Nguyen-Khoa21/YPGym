import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { CalendarDays, Clock3, Pencil, Plus, Search, UserRound } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { DataTable } from "@/components/operations/DataTable";
import { MetricCard, Modal, OperationsHeader, Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { ClassPage, GymClass, Trainer } from "@/types/operations";

const classSchema = z.object({
  title: z.string().min(3, "Use at least 3 characters.").max(160),
  class_type: z.string().min(2, "Class type is required.").max(100),
  description: z.string().max(3000).optional(),
  start_at: z.string().min(1, "Start time is required."),
  end_at: z.string().min(1, "End time is required."),
  capacity: z.number().int().min(1).max(500),
  trainer_id: z.string().optional(),
  location: z.string().min(2, "Location is required.").max(160),
}).refine((values) => new Date(values.end_at) > new Date(values.start_at), { path: ["end_at"], message: "End time must be after start time." });
type ClassForm = z.infer<typeof classSchema>;

type ClassFilters = { search: string; status: string; trainerId: string; dateFrom: string; dateTo: string };
const initialFilters: ClassFilters = { search: "", status: "", trainerId: "", dateFrom: "", dateTo: "" };

export function AdminClassesPage() {
  const { token } = useAuth();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState(initialFilters);
  const [applied, setApplied] = useState(initialFilters);
  const [editing, setEditing] = useState<GymClass | "new" | null>(null);
  const [cancelling, setCancelling] = useState<GymClass | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const query = new URLSearchParams({ page: String(page), page_size: "25" });
  if (applied.search) query.set("search", applied.search);
  if (applied.status) query.set("status", applied.status);
  if (applied.trainerId) query.set("trainer_id", applied.trainerId);
  if (applied.dateFrom) query.set("date_from", new Date(applied.dateFrom).toISOString());
  if (applied.dateTo) query.set("date_to", new Date(applied.dateTo).toISOString());
  const classes = useQuery({ queryKey: ["admin", "classes", query.toString()], queryFn: ({ signal }) => apiRequest<ClassPage>(`/admin/classes?${query}`, { token, signal }) });
  const trainers = useQuery({ queryKey: ["admin", "class-trainers"], queryFn: ({ signal }) => apiRequest<Trainer[]>("/admin/classes/trainers", { token, signal }) });
  const form = useForm<ClassForm>({ resolver: zodResolver(classSchema), defaultValues: emptyClassForm() });
  const save = useMutation({
    mutationFn: ({ id, values }: { id?: string; values: ClassForm }) => apiRequest<GymClass>(id ? `/admin/classes/${id}` : "/admin/classes", { method: id ? "PATCH" : "POST", token, body: { ...values, description: values.description || null, trainer_id: values.trainer_id || null, start_at: new Date(values.start_at).toISOString(), end_at: new Date(values.end_at).toISOString() } }),
    onSuccess: async (_, variables) => { setEditing(null); form.reset(emptyClassForm()); await queryClient.invalidateQueries({ queryKey: ["admin", "classes"] }); toast.success(variables.id ? "Class updated" : "Class scheduled"); },
    onError: (error) => toast.error(toUiError(error).message),
  });
  const cancel = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => apiRequest<GymClass>(`/admin/classes/${id}/cancel`, { method: "POST", token, body: { reason } }),
    onSuccess: async () => { setCancelling(null); setCancelReason(""); await queryClient.invalidateQueries({ queryKey: ["admin", "classes"] }); toast.success("Class cancelled"); },
    onError: (error) => toast.error(toUiError(error).message),
  });

  function openNew() { form.reset(emptyClassForm()); setEditing("new"); }
  function openEdit(item: GymClass) { form.reset({ title: item.title, class_type: item.class_type, description: item.description ?? "", start_at: toLocalDateTime(item.start_at), end_at: toLocalDateTime(item.end_at), capacity: item.capacity, trainer_id: item.trainer_id ?? "", location: item.location }); setEditing(item); }
  const columns: ColumnDef<GymClass>[] = [
    { header: "Class", cell: ({ row }) => <div><strong>{row.original.title}</strong><p className="mt-1 text-[11px] text-muted-foreground">{row.original.class_type} / {row.original.location}</p></div> },
    { header: "Schedule", cell: ({ row }) => <div><strong>{formatDateTime(row.original.start_at)}</strong><p className="mt-1 text-[11px] text-muted-foreground">to {formatDateTime(row.original.end_at)}</p></div> },
    { header: "Trainer", cell: ({ row }) => row.original.trainer_name ?? "Unassigned" },
    { header: "Capacity", accessorKey: "capacity" },
    { header: "Status", cell: ({ row }) => <StatusBadge value={row.original.status} /> },
    { header: "Actions", cell: ({ row }) => row.original.status === "scheduled" ? <div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => openEdit(row.original)}><Pencil className="size-4" /> Edit</Button><Button variant="danger" onClick={() => setCancelling(row.original)}>Cancel</Button></div> : <span className="text-xs text-muted-foreground">No actions</span> },
  ];
  const nextClass = classes.data?.items.find((item) => item.status === "scheduled");
  return <AdminShell><div className="mx-auto max-w-7xl">
    <OperationsHeader kicker="Class and schedule management" title="Program the week." description="Create, update, filter, and explicitly cancel real classes with trainer, location, capacity, timezone, and overlap validation." actions={<Button onClick={openNew}><Plus className="size-4" /> Add class</Button>} />
    {classes.data ? <div className="ops-metrics"><MetricCard label="Filtered classes" value={classes.data.page.total} /><MetricCard label="Scheduled" value={classes.data.scheduled_count} tone="forest" /><MetricCard label="Cancelled" value={classes.data.cancelled_count} tone="coral" /><MetricCard label="Available trainers" value={trainers.data?.length ?? "-"} tone="lime" /></div> : null}
    <div className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
      <Panel title="Class schedule" detail="The visible filters are enforced by the list endpoint."><form className="ops-toolbar" onSubmit={(event) => { event.preventDefault(); setApplied(filters); setPage(1); }}><Search className="size-4 text-muted-foreground" /><input aria-label="Search classes" placeholder="Title or class type" value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} /><select aria-label="Filter class status" value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">All statuses</option><option value="scheduled">Scheduled</option><option value="cancelled">Cancelled</option><option value="completed">Completed</option></select><select aria-label="Filter trainer" value={filters.trainerId} onChange={(event) => setFilters((current) => ({ ...current, trainerId: event.target.value }))}><option value="">All trainers</option>{trainers.data?.map((trainer) => <option value={trainer.id} key={trainer.id}>{trainer.display_name}</option>)}</select><input aria-label="Classes from" type="datetime-local" value={filters.dateFrom} onChange={(event) => setFilters((current) => ({ ...current, dateFrom: event.target.value }))} /><input aria-label="Classes to" type="datetime-local" value={filters.dateTo} onChange={(event) => setFilters((current) => ({ ...current, dateTo: event.target.value }))} /><Button type="submit" variant="secondary">Apply</Button></form>
        {classes.isLoading ? <LoadingState className="m-4" title="Loading class schedule" /> : null}{classes.isError ? <ErrorState className="m-4" title={toUiError(classes.error).title} message={toUiError(classes.error).message} action={<Button variant="outline" onClick={() => classes.refetch()}>Retry</Button>} /> : null}{classes.data?.items.length === 0 ? <EmptyState className="m-4" title="No classes match" message="Adjust the schedule filters or add a future class." /> : null}{classes.data?.items.length ? <><DataTable columns={columns} data={classes.data.items} getRowId={(row) => row.id} label="Admin class schedule" /><Pagination page={page} pages={classes.data.page.pages} total={classes.data.page.total} onPage={setPage} /></> : null}
      </Panel>
      <div className="grid content-start gap-5"><Panel title="Next scheduled class" detail="Real backend schedule data only.">{nextClass ? <article className="p-5"><span className="inline-flex rounded-full bg-secondary px-3 py-1 text-[10px] font-black uppercase tracking-wider">{nextClass.class_type}</span><h3 className="mt-4 font-['Barlow_Condensed'] text-4xl font-bold uppercase">{nextClass.title}</h3><p className="mt-3 flex items-center gap-2 text-sm"><Clock3 className="size-4 text-primary" /> {formatDateTime(nextClass.start_at)}</p><p className="mt-2 flex items-center gap-2 text-sm"><UserRound className="size-4 text-primary" /> {nextClass.trainer_name ?? "Trainer unassigned"}</p><p className="mt-2 flex items-center gap-2 text-sm"><CalendarDays className="size-4 text-primary" /> {nextClass.location} / {nextClass.capacity} places</p><Button className="mt-5" variant="outline" onClick={() => openEdit(nextClass)}>Edit details</Button></article> : <EmptyState className="m-4" title="No upcoming class" message="Add a future class to populate this schedule card." />}</Panel><Panel title="Scope boundary" detail="Day 37-38 only."><p className="p-5 text-sm leading-6 text-muted-foreground">Trainer lookup is intentionally minimal. Member booking, capacity enrollment, cancellation windows, waitlist promotion, and full PT management remain later-day workflows.</p></Panel></div>
    </div>
    {editing ? <Modal error={(save).isError ? toUiError((save).error).message : undefined} title={editing === "new" ? "Schedule a class" : `Edit ${editing.title}`} description="Timezone, future time, capacity, trainer availability, and resource overlap are validated by the server." onClose={() => setEditing(null)}><form className="ops-modal__body" onSubmit={form.handleSubmit((values) => save.mutate({ id: editing === "new" ? undefined : editing.id, values }))}><div className="grid gap-4 sm:grid-cols-2"><Field><Label>Title</Label><Input {...form.register("title")} /><FieldError message={form.formState.errors.title?.message} /></Field><Field><Label>Class type</Label><Input {...form.register("class_type")} /><FieldError message={form.formState.errors.class_type?.message} /></Field><Field><Label>Start</Label><Input type="datetime-local" {...form.register("start_at")} /><FieldError message={form.formState.errors.start_at?.message} /></Field><Field><Label>End</Label><Input type="datetime-local" {...form.register("end_at")} /><FieldError message={form.formState.errors.end_at?.message} /></Field><Field><Label>Capacity</Label><Input type="number" min="1" max="500" {...form.register("capacity", { valueAsNumber: true })} /><FieldError message={form.formState.errors.capacity?.message} /></Field><Field><Label>Location</Label><Input {...form.register("location")} /><FieldError message={form.formState.errors.location?.message} /></Field><Field className="sm:col-span-2"><Label>Trainer</Label><select className="h-11 rounded-md border border-input px-3" {...form.register("trainer_id")}><option value="">Unassigned</option>{trainers.data?.map((trainer) => <option value={trainer.id} key={trainer.id}>{trainer.display_name}{trainer.specialty ? ` - ${trainer.specialty}` : ""}</option>)}</select></Field><Field className="sm:col-span-2"><Label>Description</Label><textarea className="min-h-24 rounded-md border border-input p-3 text-sm" {...form.register("description")} /></Field></div><div className="ops-modal__actions"><Button type="button" variant="outline" onClick={() => setEditing(null)}>Cancel</Button><Button type="submit" disabled={save.isPending}>{editing === "new" ? "Schedule class" : "Save changes"}</Button></div></form></Modal> : null}
    {cancelling ? <Modal error={(cancel).isError ? toUiError((cancel).error).message : undefined} title={`Cancel ${cancelling.title}?`} description="Cancellation is an audited status transition; the class is never hard-deleted." onClose={() => { setCancelling(null); setCancelReason(""); }}><div className="ops-modal__body"><label>Mandatory cancellation reason<textarea value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} /></label><div className="ops-modal__actions"><Button variant="outline" onClick={() => { setCancelling(null); setCancelReason(""); }}>Keep class</Button><Button variant="danger" disabled={cancelReason.trim().length < 10 || cancel.isPending} onClick={() => cancel.mutate({ id: cancelling.id, reason: cancelReason.trim() })}>Confirm cancellation</Button></div></div></Modal> : null}
  </div></AdminShell>;
}

function emptyClassForm(): ClassForm { const start = new Date(Date.now() + 24 * 60 * 60 * 1000); start.setMinutes(0, 0, 0); const end = new Date(start.getTime() + 60 * 60 * 1000); return { title: "", class_type: "", description: "", start_at: toLocalDateTime(start.toISOString()), end_at: toLocalDateTime(end.toISOString()), capacity: 20, trainer_id: "", location: "" }; }
function toLocalDateTime(value: string) { const dateValue = new Date(value); const offset = dateValue.getTimezoneOffset(); return new Date(dateValue.getTime() - offset * 60_000).toISOString().slice(0, 16); }
