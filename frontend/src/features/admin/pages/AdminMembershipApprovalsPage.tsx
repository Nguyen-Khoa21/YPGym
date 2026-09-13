import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, ClipboardCheck, XCircle } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { MetricCard, Modal, OperationsHeader, Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDate, formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { MembershipApproval, MembershipApprovalPage } from "@/types/operations";

type Decision = { request: MembershipApproval; approve: boolean; outcome?: string };

export function AdminMembershipApprovalsPage() {
  const { token } = useAuth();
  const [status, setStatus] = useState("pending");
  const [page, setPage] = useState(1);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [reason, setReason] = useState("");
  const requests = useQuery({
    queryKey: ["admin", "membership-approvals", status, page],
    queryFn: ({ signal }) => apiRequest<MembershipApprovalPage>(`/admin/membership-requests?page=${page}&page_size=20${status ? `&status=${status}` : ""}`, { token, signal }),
  });
  const decide = useMutation({
    mutationFn: ({ request, approve, outcome }: Decision) => apiRequest(
      request.request_type === "freeze" ? `/admin/freeze-requests/${request.id}/decision` : `/admin/cancellation-requests/${request.id}/decision`,
      { method: "POST", token, body: { approve, decision_reason: reason.trim(), outcome } },
    ),
    onSuccess: async () => {
      setDecision(null);
      setReason("");
      await queryClient.invalidateQueries({ queryKey: ["admin", "membership-approvals"] });
      toast.success("Membership decision recorded");
    },
    onError: (error) => toast.error(toUiError(error).message),
  });

  const pendingOnPage = requests.data?.items.filter((item) => item.status === "pending").length ?? 0;
  return <AdminShell><div className="mx-auto max-w-6xl">
    <OperationsHeader kicker="Manager operations" title="Review with context." description="A limited queue for freeze and cancellation decisions. Full CRM and billing remain admin-only." />
    {requests.data ? <div className="ops-metrics"><MetricCard label="Matching requests" value={requests.data.page.total} tone="forest" /><MetricCard label="Pending on page" value={pendingOnPage} tone="lime" /><MetricCard label="Decision evidence" value="Required" detail="Reason and reviewer" /><MetricCard label="CRM exposure" value="Limited" tone="coral" /></div> : null}
    <Panel title="Membership approvals" detail="Newest requests appear first; every approval or rejection is audited." actions={<select aria-label="Filter approval status" className="h-10 rounded-md border border-input bg-background px-3 text-sm" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="">All statuses</option></select>}>
      {requests.isLoading ? <LoadingState className="m-4" title="Loading approval queue" /> : null}
      {requests.isError ? <ErrorState className="m-4" title={toUiError(requests.error).title} message={toUiError(requests.error).message} action={<Button variant="outline" onClick={() => requests.refetch()}>Retry</Button>} /> : null}
      {requests.data?.items.length === 0 ? <EmptyState className="m-4" title="No requests match" message="There are no membership requests in this decision state." /> : null}
      {requests.data?.items.length ? <div className="grid gap-3 p-4">{requests.data.items.map((request) => <article className="rounded-xl border border-border p-4" key={request.id}><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">{request.request_type} request</p><h2 className="mt-1 text-lg font-bold">{request.user_name}</h2><p className="text-xs text-muted-foreground">{request.user_email} / submitted {formatDateTime(request.created_at)}</p></div><StatusBadge value={request.status} /></div><p className="mt-4 text-sm leading-6">{request.reason}</p>{request.requested_start_date ? <p className="mt-2 text-xs font-bold text-muted-foreground">Requested period: {formatDate(request.requested_start_date)} to {formatDate(request.requested_end_date!)}</p> : null}{request.status === "pending" ? <div className="mt-4 flex flex-wrap gap-2">{request.request_type === "freeze" ? <Button variant="secondary" onClick={() => setDecision({ request, approve: true })}><CheckCircle2 className="size-4" /> Approve freeze</Button> : <><Button variant="secondary" onClick={() => setDecision({ request, approve: true, outcome: "refund" })}>Refund</Button><Button variant="outline" onClick={() => setDecision({ request, approve: true, outcome: "account_credit" })}>Account credit</Button><Button variant="outline" onClick={() => setDecision({ request, approve: true, outcome: "forfeit" })}>Forfeit</Button></>}<Button variant="danger" onClick={() => setDecision({ request, approve: false })}><XCircle className="size-4" /> Reject</Button></div> : <p className="mt-3 text-xs text-muted-foreground">{request.decision_reason}{request.outcome ? ` / ${request.outcome}` : ""}</p>}</article>)}</div> : null}
      {requests.data ? <Pagination page={page} pages={requests.data.page.pages} total={requests.data.page.total} onPage={setPage} /> : null}
    </Panel>
    <p className="mt-4 flex items-center gap-2 text-xs text-muted-foreground"><ClipboardCheck className="size-4" /> Managers see only the identity and request context needed to decide; admins retain the full member-detail workflow.</p>
    {decision ? <Modal error={(decide).isError ? toUiError((decide).error).message : undefined} title={`${decision.approve ? "Approve" : "Reject"} ${decision.request.request_type}`} description="The decision reason and financial outcome become part of the permanent audit trail." onClose={() => { setDecision(null); setReason(""); }}><div className="ops-modal__body"><label>Decision reason<textarea value={reason} onChange={(event) => setReason(event.target.value)} /></label><div className="ops-modal__actions"><Button variant="outline" onClick={() => { setDecision(null); setReason(""); }}>Cancel</Button><Button variant={decision.approve ? "primary" : "danger"} disabled={reason.trim().length < 10 || decide.isPending} onClick={() => decide.mutate(decision)}>Confirm decision</Button></div></div></Modal> : null}
  </div></AdminShell>;
}
