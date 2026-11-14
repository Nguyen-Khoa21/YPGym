import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CalendarDays,
  CircleUserRound,
  Clock3,
  Dumbbell,
  MapPin,
  RefreshCw,
} from "lucide-react";
import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import { EmptyState, ErrorState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { routePaths } from "@/app/routes";
import { useAuth } from "@/features/auth/AuthContext";
import { useOnboarding, useRecommendations } from "@/features/onboarding/onboardingApi";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import type { MemberDashboardPayload } from "@/types/operations";
import { EmbeddedQr } from "../components/EmbeddedQr";
import { DashboardTabs } from "../components/DashboardTabs";
import { ExpiredMembershipPanel } from "../components/ExpiredMembershipPanel";
import { OccupancyCard } from "../components/OccupancyCard";
import { TrafficHistory } from "../components/TrafficHistory";
import { gymDisplayName, visibleQuickActions } from "../memberDashboardLogic";
import { useTrafficSummary } from "../useMemberQueries";

const ONBOARDING_PROMPTED_KEY = "ypgym:onboarding:prompted";
const actionIcons = { membership: RefreshCw, classes: CalendarDays, profile: CircleUserRound };

export function MemberDashboardPage() {
  const { token } = useAuth();
  const query = useQuery({
    queryKey: ["dashboard", "me"],
    queryFn: ({ signal }) => apiRequest<MemberDashboardPayload>("/dashboard/me", { token, signal }),
    refetchInterval: 30_000,
  });
  const hasMembership = Boolean(query.data?.membership);
  const traffic = useTrafficSummary(hasMembership);
  const navigate = useNavigate();
  const onboarding = useOnboarding();
  const recommendations = useRecommendations();
  const onboardingStatus = onboarding.data?.status;
  useEffect(() => {
    // Ask the questionnaire once, right after the first login. Skipping or answering stores the status server-side.
    if (onboardingStatus !== "not_started") return;
    try {
      if (window.sessionStorage.getItem(ONBOARDING_PROMPTED_KEY)) return;
      window.sessionStorage.setItem(ONBOARDING_PROMPTED_KEY, "1");
    } catch {
      /* storage unavailable: still ask once per page load */
    }
    navigate(routePaths.memberOnboarding, { replace: true });
  }, [navigate, onboardingStatus]);
  if (query.isLoading)
    return (
      <MemberShell>
        <DashboardSkeleton />
      </MemberShell>
    );
  if (query.isError)
    return (
      <MemberShell>
        <div className="mx-auto max-w-6xl">
          <ErrorState
            title={toUiError(query.error).title}
            message={toUiError(query.error).message}
            action={
              <Button variant="outline" onClick={() => query.refetch()}>
                Retry dashboard
              </Button>
            }
          />
        </div>
      </MemberShell>
    );
  if (!query.data) return null;
  const data = query.data;
  const next = data.upcoming_bookings[0];
  return (
    <MemberShell>
      <div className="mx-auto grid max-w-6xl gap-5">
        <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
          <div className="min-w-0">
            <p className="text-xs font-black uppercase tracking-[0.14em] text-muted-foreground">
              Member dashboard
            </p>
            <h1 className="mt-1 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none sm:text-5xl">
              Hi, {data.member.name.split(" ")[0]}
            </h1>
          </div>
          {data.membership ? (
            <p
              className="inline-flex items-center gap-2 font-['Barlow_Condensed'] text-3xl font-bold uppercase leading-none text-primary sm:text-4xl"
              data-testid="member-gym"
            >
              <MapPin className="size-6" aria-hidden />
              {gymDisplayName(data.membership.home_gym_name)}
            </p>
          ) : (
            <p className="text-sm font-semibold">No gym selected yet</p>
          )}
          {next ? (
            <p className="w-full text-sm text-muted-foreground">
              Your next class is {next.gym_class.title} at {formatDateTime(next.gym_class.start_at)}
              .
            </p>
          ) : null}
        </header>
        <ExpiredMembershipPanel membership={data.membership} />
        {recommendations.data?.quiet_hours ? (
          <section
            className="flex items-start gap-3 rounded-2xl border border-border bg-card p-4"
            aria-label="Quiet time for you"
          >
            <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-secondary text-foreground">
              <Clock3 className="size-4" aria-hidden />
            </span>
            <p className="text-sm">
              <strong>Quiet time for you: {recommendations.data.quiet_hours.label}</strong> at{" "}
              {recommendations.data.quiet_hours.gym_name}
              <span className="block text-xs text-muted-foreground">
                Based on last month's attendance at that gym.
              </span>
            </p>
          </section>
        ) : recommendations.data?.quiet_hours_reason ? (
          <section
            className="flex items-start gap-3 rounded-2xl border border-border bg-card p-4"
            aria-label="Quiet time for you"
          >
            <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground">
              <Clock3 className="size-4" aria-hidden />
            </span>
            <p className="text-sm">Not enough attendance data yet to suggest a quiet time.</p>
          </section>
        ) : null}
        {data.membership ? (
          <>
            <div className="grid gap-5 lg:grid-cols-[1.3fr_0.7fr]">
              <div className="grid content-start gap-5">
                {data.crowdedness ? <OccupancyCard data={data.crowdedness} /> : null}
                <TrafficHistory query={traffic} gymName={data.membership.home_gym_name} />
              </div>
              <div className="self-start">
                <EmbeddedQr eligible={data.qr_access.eligible} reason={data.qr_access.reason} />
              </div>
            </div>
            <DashboardTabs
              broadcasts={data.active_broadcasts}
              notifications={data.recent_notifications}
              unreadCount={data.unread_notification_count}
              membership={data.membership}
            />
          </>
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6">
              <h2 className="text-xl font-bold">Choose your gym</h2>
              <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
                Buy a membership and pick a location to see live occupancy, quiet times and your
                check-in code.
              </p>
              <Link
                className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
                to="/memberships"
              >
                Buy membership <ArrowRight className="size-4" aria-hidden />
              </Link>
            </section>
            <DashboardTabs
              broadcasts={data.active_broadcasts}
              notifications={data.recent_notifications}
              unreadCount={data.unread_notification_count}
              membership={data.membership}
            />
          </>
        )}
        <section className="grid gap-5">
          <article className="rounded-2xl border border-border bg-card p-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold">Upcoming bookings</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Your next three confirmed classes.
                </p>
              </div>
              <Link className="text-sm font-bold text-primary" to="/app/bookings">
                View all
              </Link>
            </div>
            {data.upcoming_bookings.length ? (
              <ul className="mt-4 grid gap-3">
                {data.upcoming_bookings.map((booking) => (
                  <li className="rounded-xl bg-muted/50 p-4" key={booking.id}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <strong>{booking.gym_class.title}</strong>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {formatDateTime(booking.gym_class.start_at)} /{" "}
                          {booking.gym_class.location}
                        </p>
                      </div>
                      <StatusBadge value={booking.status} />
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState
                className="mt-4"
                title="No upcoming bookings"
                message="Book a class to see it here."
              />
            )}
            {data.active_waitlists.length ? (
              <div className="mt-5 border-t border-border pt-4">
                <p className="text-xs font-black uppercase tracking-wider text-muted-foreground">
                  Active waitlists
                </p>
                {data.active_waitlists.map((entry) => (
                  <p className="mt-2 text-sm" key={entry.id}>
                    {entry.gym_class.title} / position {entry.position}
                  </p>
                ))}
              </div>
            ) : null}
          </article>
        </section>
        <section className="rounded-2xl border border-border bg-card p-5">
          <h2 className="text-lg font-bold">Quick actions</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {visibleQuickActions(data.quick_actions).map((action) => {
              const Icon = actionIcons[action.key as keyof typeof actionIcons] ?? Dumbbell;
              return action.enabled ? (
                <Link
                  className="rounded-xl border border-border p-4 transition hover:-translate-y-0.5 hover:bg-muted"
                  to={action.target}
                  key={action.key}
                >
                  <Icon className="size-5 text-primary" aria-hidden />
                  <strong className="mt-3 block text-sm">{action.label}</strong>
                </Link>
              ) : (
                <div
                  className="rounded-xl border border-border bg-muted/40 p-4 text-muted-foreground"
                  aria-disabled="true"
                  title={action.reason ?? undefined}
                  key={action.key}
                >
                  <Icon className="size-5" aria-hidden />
                  <strong className="mt-3 block text-sm">{action.label}</strong>
                  <span className="mt-1 block text-xs">Unavailable</span>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </MemberShell>
  );
}

function DashboardSkeleton() {
  return (
    <div
      className="mx-auto max-w-6xl animate-pulse"
      role="status"
      aria-label="Loading member dashboard"
    >
      <div className="h-16 rounded-2xl bg-muted" />
      <div className="mt-5 grid gap-5 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="h-56 rounded-2xl bg-muted" />
        <div className="h-56 rounded-2xl bg-muted" />
      </div>
      <div className="mt-5 h-64 rounded-2xl bg-muted" />
      <span className="sr-only">Loading member dashboard</span>
    </div>
  );
}
