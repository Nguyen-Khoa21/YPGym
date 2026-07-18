import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { OperationsHeader, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDate, formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { MembershipRequest } from "@/types/operations";

const cancellationSchema = z.object({ reason: z.string().min(10, "Please provide at least 10 characters.") });
const freezeSchema = z.object({ requested_start_date: z.string().min(1, "Start date is required."), requested_end_date: z.string().min(1, "End date is required."), reason: z.string().min(10, "Please provide at least 10 characters.") });

export function MembershipRequestsPage() {
  const { token } = useAuth();
  const requests = useQuery({ queryKey: ["membership", "requests"], queryFn: ({ signal }) => apiRequest<MembershipRequest[]>("/memberships/requests/me", { token, signal }) });
  const cancellation = useForm<z.infer<typeof cancellationSchema>>({ resolver: zodResolver(cancellationSchema), defaultValues: { reason: "" } });
  const freeze = useForm<z.infer<typeof freezeSchema>>({ resolver: zodResolver(freezeSchema), defaultValues: { requested_start_date: "", requested_end_date: "", reason: "" } });
  const create = useMutation({ mutationFn: ({ path, body }: { path: string; body: unknown }) => apiRequest(path, { method: "POST", token, body }), onSuccess: async () => { cancellation.reset(); freeze.reset(); await queryClient.invalidateQueries({ queryKey: ["membership", "requests"] }); toast.success("Membership request submitted"); }, onError: (error) => toast.error(toUiError(error).message) });
  return <MemberShell><div className="mx-auto max-w-6xl"><OperationsHeader kicker="Membership operations" title="Pause or close, with clarity." description="Freeze and cancellation requests are reviewed, status-tracked and never applied silently." />
    <div className="mt-6 grid gap-5 lg:grid-cols-2"><Panel title="Request a freeze" detail="Freeze periods can be up to 90 days."><form className="grid gap-4 p-4" onSubmit={freeze.handleSubmit((values) => create.mutate({ path: "/memberships/freeze-requests", body: values }))}><div className="grid gap-4 sm:grid-cols-2"><Field><Label>Start date</Label><Input type="date" {...freeze.register("requested_start_date")} /><FieldError message={freeze.formState.errors.requested_start_date?.message} /></Field><Field><Label>End date</Label><Input type="date" {...freeze.register("requested_end_date")} /><FieldError message={freeze.formState.errors.requested_end_date?.message} /></Field></div><Field><Label>Reason</Label><textarea className="min-h-28 rounded-md border border-input p-3 text-sm" {...freeze.register("reason")} /><FieldError message={freeze.formState.errors.reason?.message} /></Field><Button type="submit" disabled={create.isPending}>Submit freeze request</Button></form></Panel>
      <Panel title="Request cancellation" detail="An approved decision must record refund, account credit or forfeit."><form className="grid gap-4 p-4" onSubmit={cancellation.handleSubmit((values) => create.mutate({ path: "/memberships/cancellation-requests", body: values }))}><Field><Label>Cancellation reason</Label><textarea className="min-h-36 rounded-md border border-input p-3 text-sm" {...cancellation.register("reason")} /><FieldError message={cancellation.formState.errors.reason?.message} /></Field><Button type="submit" variant="danger" disabled={create.isPending}>Submit cancellation request</Button></form></Panel></div>
    {requests.isLoading ? <LoadingState className="mt-6" title="Loading request history" /> : null}{requests.isError ? <ErrorState className="mt-6" title={toUiError(requests.error).title} message={toUiError(requests.error).message} /> : null}
    {requests.data ? <Panel title="Request history" detail="Open duplicates are blocked by the database."><div className="grid gap-3 p-4">{requests.data.length === 0 ? <EmptyState title="No membership requests" message="Your freeze and cancellation history will appear here." /> : requests.data.map((item) => <article className="rounded-xl border border-border p-4" key={item.id}><div className="flex flex-wrap items-center justify-between gap-3"><strong className="capitalize">{item.request_type} request</strong><StatusBadge value={item.status} /></div><p className="mt-2 text-sm">{item.reason}</p>{item.requested_start_date ? <p className="mt-2 text-xs text-muted-foreground">{formatDate(item.requested_start_date)} to {formatDate(item.requested_end_date!)}</p> : null}<p className="mt-2 text-xs text-muted-foreground">Submitted {formatDateTime(item.created_at)}</p>{item.decision_reason ? <p className="mt-2 border-l-2 border-secondary pl-3 text-xs text-muted-foreground">{item.decision_reason} {item.outcome ? `· ${item.outcome}` : ""}</p> : null}</article>)}</div></Panel> : null}
  </div></MemberShell>;
}
