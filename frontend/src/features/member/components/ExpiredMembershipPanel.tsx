import { CalendarX2 } from "lucide-react";
import { Link } from "react-router-dom";

import { isExpiredStatus, renewalSearch } from "@/features/memberships/renewalIntent";
import { formatDate } from "@/lib/format";

type PanelMembership = {
  status: string;
  home_gym_id: string;
  home_gym_name: string;
  expiry_date: string;
};

/** Shown only when the membership has expired (not cancelled, revoked or frozen). */
export function ExpiredMembershipPanel({
  membership,
}: {
  membership: PanelMembership | null | undefined;
}) {
  if (!membership || !isExpiredStatus(membership.status)) return null;
  const action =
    "inline-flex min-h-11 items-center justify-center rounded-full px-5 py-2.5 text-sm font-extrabold";
  return (
    <section
      className="rounded-2xl border border-destructive/40 bg-destructive/5 p-5"
      aria-labelledby="expired-heading"
      role="region"
    >
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-destructive/10 text-destructive">
          <CalendarX2 className="size-5" aria-hidden />
        </span>
        <div className="min-w-0">
          <h2 id="expired-heading" className="text-lg font-bold">
            Your membership at {membership.home_gym_name} expired on{" "}
            {formatDate(membership.expiry_date)}.
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Renew to use your check-in code again, or switch to another location. Your gym only
            changes after the payment is confirmed.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              className={`${action} bg-primary text-primary-foreground`}
              to={`/memberships${renewalSearch({ mode: "renew", gymId: membership.home_gym_id })}`}
            >
              Renew at {membership.home_gym_name}
            </Link>
            <Link
              className={`${action} border border-border bg-card`}
              to={`/memberships${renewalSearch({ mode: "change" })}`}
            >
              Change location
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
