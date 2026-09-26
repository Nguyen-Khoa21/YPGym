import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { OperationsHeader, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";

type Delivery = {
  id: string; user_id: string; member_name: string; recipient_masked: string;
  template_type: string; status: string; attempt_count: number; queued_at: string;
  sent_to_provider_at: string | null; last_error_category: string | null;
  invoice_id: string; invoice_number: string;
};
type DeliveryPage = { items: Delivery[]; page: number; page_size: number; total: number; pages: number };

export function AdminEmailDeliveriesPage() {
  const { token } = useAuth();
  const deliveries = useQuery({ queryKey: ["admin", "email-deliveries"], queryFn: () => apiRequest<DeliveryPage>("/admin/email-deliveries", { token }) });
  const retry = useMutation({
    mutationFn: (id: string) => apiRequest(`/admin/email-deliveries/${id}/retry`, { method: "POST", token }),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["admin", "email-deliveries"] }); toast.success("Email queued for retry"); },
    onError: (caught) => toast.error(toUiError(caught).message),
  });
  return <AdminShell><div className="mx-auto max-w-7xl">
    <OperationsHeader kicker="Transactional email" title="Delivery operations." description="SMTP acceptance is recorded as sent to provider. It does not claim inbox delivery." />
    {deliveries.isLoading ? <LoadingState title="Loading email deliveries" /> : null}
    {deliveries.isError ? <ErrorState title="Email deliveries unavailable" message={toUiError(deliveries.error).message} /> : null}
    {deliveries.data ? <Panel title={`${deliveries.data.total} delivery records`} detail="Recipients and provider failures are privacy-safe.">
      {deliveries.data.items.length ? <div className="overflow-x-auto"><table className="w-full text-left text-sm">
        <thead><tr className="border-b border-border"><th className="p-3">Member</th><th className="p-3">Message</th><th className="p-3">Invoice</th><th className="p-3">Status</th><th className="p-3">Attempts</th><th className="p-3">Queued / sent</th><th className="p-3">Action</th></tr></thead>
        <tbody>{deliveries.data.items.map((item) => <tr className="border-b border-border/70" key={item.id}>
          <td className="p-3"><Link className="font-bold text-primary hover:underline" to={`/admin/members/${item.user_id}`}>{item.member_name}</Link><small className="block text-muted-foreground">{item.recipient_masked}</small></td>
          <td className="p-3">{item.template_type.replaceAll("_", " ")}</td><td className="p-3">{item.invoice_number}</td>
          <td className="p-3"><StatusBadge value={item.status} />{item.last_error_category ? <small className="mt-1 block text-muted-foreground">{item.last_error_category.replaceAll("_", " ")}</small> : null}</td>
          <td className="p-3">{item.attempt_count}</td><td className="p-3"><span>{formatDateTime(item.queued_at)}</span>{item.sent_to_provider_at ? <small className="block text-muted-foreground">Sent {formatDateTime(item.sent_to_provider_at)}</small> : null}</td>
          <td className="p-3">{item.status === "failed" ? <Button variant="outline" disabled={retry.isPending} onClick={() => retry.mutate(item.id)}>Retry</Button> : "—"}</td>
        </tr>)}</tbody>
      </table></div> : <EmptyState title="No transactional emails" message="Purchase and renewal email intents will appear here." />}
    </Panel> : null}
  </div></AdminShell>;
}
