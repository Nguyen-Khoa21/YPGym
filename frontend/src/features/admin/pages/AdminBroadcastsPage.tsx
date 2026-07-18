import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Megaphone, RadioTower } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { OperationsHeader, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { Broadcast } from "@/types/operations";

const schema = z.object({ audience: z.enum(["all", "members", "normal", "advance", "vip"]), title: z.string().min(3), message: z.string().min(5), starts_at: z.string().min(1), ends_at: z.string().optional() });
type FormData = z.infer<typeof schema>;

export function AdminBroadcastsPage() {
  const { token } = useAuth();
  const broadcasts = useQuery({ queryKey: ["admin", "broadcasts"], queryFn: ({ signal }) => apiRequest<Broadcast[]>("/admin/broadcasts", { token, signal }) });
  const form = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { audience: "all", title: "", message: "", starts_at: localDateTime(new Date()), ends_at: "" } });
  const create = useMutation({ mutationFn: (values: FormData) => apiRequest<Broadcast>("/admin/broadcasts", { method: "POST", token, body: { ...values, starts_at: new Date(values.starts_at).toISOString(), ends_at: values.ends_at ? new Date(values.ends_at).toISOString() : null } }), onSuccess: async () => { form.reset({ audience: "all", title: "", message: "", starts_at: localDateTime(new Date()), ends_at: "" }); await queryClient.invalidateQueries({ queryKey: ["admin", "broadcasts"] }); toast.success("Broadcast published"); }, onError: (error) => toast.error(toUiError(error).message) });
  const deactivate = useMutation({ mutationFn: (id: string) => apiRequest(`/admin/broadcasts/${id}`, { method: "PATCH", token, body: { is_active: false } }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "broadcasts"] }), onError: (error) => toast.error(toUiError(error).message) });
  return <AdminShell><div className="mx-auto max-w-6xl"><OperationsHeader kicker="Member communications" title="Broadcast with an expiry." description="Active periods and audiences are enforced by the backend; inactive or expired announcements never masquerade as current." />
    <div className="mt-6 grid gap-5 lg:grid-cols-[0.8fr_1.2fr]"><Panel title="Publish announcement" detail="Creation and sensitive edits are audited."><form className="grid gap-4 p-4" onSubmit={form.handleSubmit((values) => create.mutate(values))}><Field><Label>Audience</Label><select className="h-11 rounded-md border border-input px-3" {...form.register("audience")}><option value="all">Everyone</option><option value="members">All members</option><option value="normal">Normal tier</option><option value="advance">Advance tier</option><option value="vip">VIP tier</option></select></Field><Field><Label>Title</Label><Input {...form.register("title")} /><FieldError message={form.formState.errors.title?.message} /></Field><Field><Label>Message</Label><textarea className="min-h-28 rounded-md border border-input p-3 text-sm" {...form.register("message")} /><FieldError message={form.formState.errors.message?.message} /></Field><div className="grid gap-4 sm:grid-cols-2"><Field><Label>Starts</Label><Input type="datetime-local" {...form.register("starts_at")} /></Field><Field><Label>Ends (optional)</Label><Input type="datetime-local" {...form.register("ends_at")} /></Field></div><Button type="submit" disabled={create.isPending}><Megaphone className="size-4" /> Publish broadcast</Button></form></Panel>
      <Panel title="Announcement history" detail="Member dashboards fetch only active, preference-eligible records.">{broadcasts.isLoading ? <LoadingState className="m-4" title="Loading broadcasts" /> : null}{broadcasts.isError ? <ErrorState className="m-4" title={toUiError(broadcasts.error).title} message={toUiError(broadcasts.error).message} /> : null}{broadcasts.data?.length === 0 ? <EmptyState className="m-4" title="No broadcasts" message="Publish the first gym announcement." /> : null}<div className="grid gap-3 p-4">{broadcasts.data?.map((item) => <article className="rounded-xl border border-border p-4" key={item.id}><div className="flex items-start gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary text-secondary"><RadioTower className="size-5" /></span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><strong>{item.title}</strong><StatusBadge value={item.is_active ? "active" : "inactive"} /></div><p className="mt-2 text-sm leading-6 text-muted-foreground">{item.message}</p><p className="mt-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{item.audience} · starts {formatDateTime(item.starts_at)}</p>{item.is_active ? <Button className="mt-3" variant="outline" disabled={deactivate.isPending} onClick={() => deactivate.mutate(item.id)}>Deactivate</Button> : null}</div></div></article>)}</div></Panel></div>
  </div></AdminShell>;
}

function localDateTime(value: Date) { const offset = value.getTimezoneOffset(); return new Date(value.getTime() - offset * 60_000).toISOString().slice(0, 16); }
