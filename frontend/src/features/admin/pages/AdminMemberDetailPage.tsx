import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Ban, CalendarClock, CreditCard, ShieldAlert } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { MetricCard, Modal, OperationsHeader, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDate, formatDateTime, formatMoney } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { AdminMemberDetail, MembershipRequest } from "@/types/operations";

type Decision = { request: MembershipRequest; approve: boolean; outcome?: string };

export function AdminMemberDetailPage() {
  const { id = "" } = useParams();
  const { token } = useAuth();
  const [decision, setDecision] = useState<Decision | null>(null);
  const [revokeOpen, setRevokeOpen] = useState(false);
  const [reason, setReason] = useState("");
  const detail = useQuery({ queryKey: ["admin", "members", id], queryFn: ({ signal }) => apiRequest<AdminMemberDetail>(`/admin/members/${id}`, { token, signal }), enabled: Boolean(id) });
  const action = useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) => apiRequest(path, { method: "POST", token, body }),
    onSuccess: async () => { setDecision(null); setRevokeOpen(false); setReason(""); await queryClient.invalidateQueries({ queryKey: ["admin", "members"] }); toast.success("Membership action recorded"); },
    onError: (error) => toast.error(toUiError(error).message),
  });

  if (detail.isLoading) return <AdminShell><LoadingState title="Loading member record" /></AdminShell>;
  if (detail.isError || !detail.data) return <AdminShell><ErrorState title={toUiError(detail.error).title} message={toUiError(detail.error).message} /></AdminShell>;
  const data = detail.data;
  const current = data.memberships[0];
  return <AdminShell><div className="mx-auto max-w-7xl">
    <Link className="mb-5 inline-flex items-center gap-2 text-xs font-extrabold text-muted-foreground hover:text-foreground" to="/admin/members"><ArrowLeft className="size-4" /> Back to CRM</Link>
    <OperationsHeader kicker="Admin member details" title={data.profile.name} description={`${data.profile.email} · ${data.profile.phone}`} actions={<Button variant="danger" disabled={!current || current.status === "revoked"} onClick={() => setRevokeOpen(true)}><Ban className="size-4" /> Revoke access</Button>} />
    <div className="ops-metrics"><MetricCard label="Membership" value={current?.status ?? "None"} tone="forest" detail={current?.plan_name} /><MetricCard label="Total visits" value={data.attendance_summary.total_visits} tone="lime" /><MetricCard label="Payments" value={data.payments.length} detail={data.payments[0] ? formatMoney(data.payments[0].amount) + " latest" : "No payments"} /><MetricCard label="Bookings" value={data.booking_summary.total} tone="coral" detail={`${data.booking_summary.waitlisted} waitlisted`} /></div>
    <div className="mt-5 grid gap-5 xl:grid-cols-[0.72fr_1.28fr]">
      <div><Panel title="Customer profile"><div className="grid gap-4 p-5 text-sm"><div className="grid size-16 place-items-center rounded-2xl bg-secondary text-2xl font-black">{data.profile.name[0]}</div><Info label="Role and tier" value={`${data.profile.role} · ${data.profile.tier}`} /><Info label="Email" value={data.profile.email} /><Info label="Phone" value={data.profile.phone} /><Info label="Verification" value={data.profile.is_email_verified ? "Verified" : "Pending"} /></div></Panel>
      <Panel title="Membership history" detail="Lifecycle state is centrally enforced."><div className="grid gap-3 p-4">{data.memberships.map((item) => <article className="rounded-xl border border-border p-4" key={item.id}><div className="flex items-center justify-between gap-3"><strong>{item.plan_name}</strong><StatusBadge value={item.status} /></div><p className="mt-2 text-xs text-muted-foreground">{formatDate(item.start_date)} to {formatDate(item.expiry_date)}</p>{item.frozen_from ? <p className="mt-1 text-xs text-muted-foreground">Freeze: {formatDate(item.frozen_from)} to {formatDate(item.frozen_until!)}</p> : null}</article>)}</div></Panel></div>
      <div><Panel title="Membership operations" detail="Decisions require a reason and are written to the audit trail."><div className="grid gap-3 p-4">{data.membership_requests.length === 0 ? <p className="text-sm text-muted-foreground">No freeze or cancellation requests.</p> : data.membership_requests.map((request) => <article className="rounded-xl border border-border p-4" key={request.id}><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-black uppercase tracking-wider">{request.request_type}</p><p className="mt-1 text-sm">{request.reason}</p></div><StatusBadge value={request.status} /></div>{request.status === "pending" ? <div className="mt-4 flex flex-wrap gap-2">{request.request_type === "freeze" ? <Button variant="secondary" onClick={() => setDecision({ request, approve: true })}>Approve freeze</Button> : <><Button variant="secondary" onClick={() => setDecision({ request, approve: true, outcome: "refund" })}>Refund</Button><Button variant="outline" onClick={() => setDecision({ request, approve: true, outcome: "account_credit" })}>Credit</Button><Button variant="outline" onClick={() => setDecision({ request, approve: true, outcome: "forfeit" })}>Forfeit</Button></>}<Button variant="danger" onClick={() => setDecision({ request, approve: false })}>Reject</Button></div> : <p className="mt-2 text-xs text-muted-foreground">{request.decision_reason} {request.outcome ? `· ${request.outcome}` : ""}</p>}</article>)}</div></Panel>
      <Panel title="Billing & attendance"><div className="grid gap-5 p-4 lg:grid-cols-2"><div><h3 className="flex items-center gap-2 text-lg font-bold"><CreditCard className="size-4" /> Latest payments</h3>{data.payments.slice(0, 4).map((item) => <div className="mt-3 border-t border-border pt-3 text-xs" key={item.id}><div className="flex justify-between gap-3"><strong>{item.plan_name}</strong><span>{formatMoney(item.amount)}</span></div><p className="mt-1 text-muted-foreground">{formatDateTime(item.created_at)}</p></div>)}</div><div><h3 className="flex items-center gap-2 text-lg font-bold"><CalendarClock className="size-4" /> Recent visits</h3>{data.attendance_history.slice(0, 4).map((item) => <div className="mt-3 border-t border-border pt-3 text-xs" key={item.id}><div className="flex justify-between gap-3"><strong>{formatDateTime(item.checked_in_at)}</strong><StatusBadge value={item.status} /></div><p className="mt-1 text-muted-foreground">{item.device_id ?? item.source}</p></div>)}</div></div></Panel>
      <Panel title="Relevant audit trail"><div className="grid gap-3 p-4">{data.audit_logs.slice(0, 8).map((item) => <article className="border-l-2 border-secondary pl-3 text-xs" key={item.id}><div className="flex justify-between gap-3"><strong>{item.action}</strong><span className="text-muted-foreground">{formatDateTime(item.created_at)}</span></div><p className="mt-1 text-muted-foreground">{item.summary}</p></article>)}</div></Panel></div>
    </div>
    {decision ? <Modal error={(action).isError ? toUiError((action).error).message : undefined} title={`${decision.approve ? "Approve" : "Reject"} ${decision.request.request_type}`} description="This reason becomes part of the permanent audit record." onClose={() => { setDecision(null); setReason(""); }}><div className="ops-modal__body"><label>Decision reason<textarea value={reason} onChange={(event) => setReason(event.target.value)} /></label><div className="ops-modal__actions"><Button variant="outline" onClick={() => setDecision(null)}>Cancel</Button><Button variant={decision.approve ? "primary" : "danger"} disabled={reason.trim().length < 10 || action.isPending} onClick={() => action.mutate({ path: decision.request.request_type === "freeze" ? `/admin/freeze-requests/${decision.request.id}/decision` : `/admin/cancellation-requests/${decision.request.id}/decision`, body: { approve: decision.approve, decision_reason: reason, outcome: decision.outcome } })}>Confirm decision</Button></div></div></Modal> : null}
    {revokeOpen ? <Modal error={(action).isError ? toUiError((action).error).message : undefined} title="Revoke membership access" description="QR generation and class access will be blocked immediately." onClose={() => { setRevokeOpen(false); setReason(""); }}><div className="ops-modal__body"><div className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive"><ShieldAlert className="mb-2 size-5" /> Revocation is a sensitive action and cannot be silent.</div><label>Mandatory reason<textarea value={reason} onChange={(event) => setReason(event.target.value)} /></label><div className="ops-modal__actions"><Button variant="outline" onClick={() => setRevokeOpen(false)}>Cancel</Button><Button variant="danger" disabled={reason.trim().length < 10 || action.isPending} onClick={() => action.mutate({ path: `/admin/members/${id}/revoke`, body: { reason } })}>Revoke membership</Button></div></div></Modal> : null}
  </div></AdminShell>;
}

function Info({ label, value }: { label: string; value: string }) { return <div><p className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-semibold capitalize">{value}</p></div>; }
