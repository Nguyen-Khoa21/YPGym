import { ArrowRight, MapPin } from "lucide-react";
import { Link } from "react-router-dom";

import { StatusBadge } from "@/components/operations/OperationsUi";
import { routePaths } from "@/app/routes";
import { useAuth } from "@/features/auth/AuthContext";
import { formatDate } from "@/lib/format";
import { gymDisplayName } from "../memberDashboardLogic";
import { useMemberDashboard } from "../useMemberQueries";

/** The signed-in member's current membership. Renders nothing for other roles or while loading. */
export function MembershipStatusCard({
  className = "",
  showPlansLink = true,
}: {
  className?: string;
  showPlansLink?: boolean;
}) {
  const { user } = useAuth();
  const isMember = user?.role === "member";
  const dashboard = useMemberDashboard(isMember);
  if (!isMember || !dashboard.data) return null;
  const membership = dashboard.data.membership;

  return (
    <section
      className={`rounded-2xl border border-border bg-card p-5 ${className}`}
      aria-labelledby="membership-status-heading"
    >
      <h2
        id="membership-status-heading"
        className="text-xs font-black uppercase tracking-wider text-muted-foreground"
      >
        Membership status
      </h2>
      {membership ? (
        <>
          <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
            <strong className="text-lg">{membership.plan_name}</strong>
            <StatusBadge value={membership.status} />
          </div>
          <p className="mt-2 text-sm">
            {membership.days_remaining} days remaining · expires{" "}
            {formatDate(membership.expiry_date)}
          </p>
          <p className="mt-1 inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <MapPin className="size-3.5" aria-hidden />
            {gymDisplayName(membership.home_gym_name)} · {membership.message}
          </p>
          {showPlansLink ? (
            <Link
              className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-primary"
              to={routePaths.membershipPlans}
            >
              Renew membership <ArrowRight className="size-4" aria-hidden />
            </Link>
          ) : null}
        </>
      ) : (
        <>
          <p className="mt-2 text-sm text-muted-foreground">You do not have a membership yet.</p>
          {showPlansLink ? (
            <Link
              className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-primary"
              to={routePaths.membershipPlans}
            >
              Buy membership <ArrowRight className="size-4" aria-hidden />
            </Link>
          ) : null}
        </>
      )}
    </section>
  );
}
