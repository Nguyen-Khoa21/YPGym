import { useQuery } from "@tanstack/react-query";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime, formatMoney } from "@/lib/format";

type AdminBillingItem = {
  payment_id: string;
  user_id: string;
  member_name: string;
  member_email: string;
  plan_name: string;
  amount: string;
  status: string;
  created_at: string;
};

export function AdminBillingPage() {
  const { token } = useAuth();
  const billing = useQuery({
    queryKey: ["admin", "billing"],
    queryFn: () =>
      apiRequest<AdminBillingItem[]>("/billing/admin/payments", { token }),
  });

  return (
    <AppFrame>
      <main className="mx-auto max-w-6xl px-5 py-10">
        <div className="mb-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-primary">
            Admin billing
          </p>
          <h1 className="mt-2 text-3xl font-bold">Billing Placeholder</h1>
          <p className="mt-2 text-muted-foreground">
            A lightweight Day 20 view for recent member payments. Full billing
            administration is reserved for the admin module later.
          </p>
        </div>

        {billing.isLoading ? <LoadingState title="Loading admin billing" /> : null}

        {billing.isError ? (
          <ErrorState
            title={toUiError(billing.error).title}
            message={toUiError(billing.error).message}
          />
        ) : null}

        {billing.isSuccess && billing.data.length === 0 ? (
          <EmptyState
            title="No payments yet"
            message="Member mock purchases will appear in this table."
          />
        ) : null}

        {billing.isSuccess && billing.data.length > 0 ? (
          <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-muted text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Member</th>
                    <th className="px-4 py-3 font-semibold">Plan</th>
                    <th className="px-4 py-3 font-semibold">Amount</th>
                    <th className="px-4 py-3 font-semibold">Status</th>
                    <th className="px-4 py-3 font-semibold">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {billing.data.map((item) => (
                    <tr key={item.payment_id} className="border-t border-border">
                      <td className="px-4 py-3">
                        <p className="font-semibold">{item.member_name}</p>
                        <p className="text-muted-foreground">{item.member_email}</p>
                      </td>
                      <td className="px-4 py-3">{item.plan_name}</td>
                      <td className="px-4 py-3 font-semibold">
                        {formatMoney(item.amount)}
                      </td>
                      <td className="px-4 py-3">{item.status}</td>
                      <td className="px-4 py-3">{formatDateTime(item.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </main>
    </AppFrame>
  );
}
