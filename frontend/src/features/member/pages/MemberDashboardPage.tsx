import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Bell, CalendarDays, CircleUserRound, Dumbbell, Megaphone, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDate, formatDateTime } from "@/lib/format";
import type { MemberDashboardPayload } from "@/types/operations";
import { EmbeddedQr } from "../components/EmbeddedQr";
import { OccupancyCard } from "../components/OccupancyCard";
import { TrafficHistory } from "../components/TrafficHistory";
import { dedupeNotifications, visibleQuickActions } from "../memberDashboardLogic";
import { useTrafficSummary } from "../useMemberQueries";

const actionIcons = { membership: RefreshCw, classes: CalendarDays, profile: CircleUserRound };

export function MemberDashboardPage() {
  const { token } = useAuth();
  const query = useQuery({ queryKey: ["dashboard", "me"], queryFn: ({ signal }) => apiRequest<MemberDashboardPayload>("/dashboard/me", { token, signal }), refetchInterval: 30_000 });
  const hasMembership = Boolean(query.data?.membership);
  const traffic = useTrafficSummary(hasMembership);
  if (query.isLoading) return <MemberShell><DashboardSkeleton /></MemberShell>;
  if (query.isError) return <MemberShell><div className="mx-auto max-w-6xl"><ErrorState title={toUiError(query.error).title} message={toUiError(query.error).message} action={<Button variant="outline" onClick={() => query.refetch()}>Retry dashboard</Button>} /></div></MemberShell>;
  if (!query.data) return null;
  const data = query.data;
  const next = data.upcoming_bookings[0];
  const notifications = dedupeNotifications(data.recent_notifications, data.active_broadcasts);
  return <MemberShell><div className="mx-auto grid max-w-6xl gap-5">
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
      <div className="min-w-0"><p className="text-xs font-black uppercase tracking-[0.14em] text-muted-foreground">Member dashboard</p><h1 className="mt-1 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none sm:text-5xl">Hi, {data.member.name.split(" ")[0]}</h1></div>
      <p className="text-sm font-semibold">{data.membership ? `Your gym: ${data.membership.home_gym_name}` : "No gym selected yet"}</p>
      {next ? <p className="w-full text-sm text-muted-foreground">Your next class is {next.gym_class.title} at {formatDateTime(next.gym_class.start_at)}.</p> : null}
    </header>
    {data.active_broadcasts.length ? <section className="grid gap-3" aria-label="Announcements">{data.active_broadcasts.map((item) => <article className="rounded-2xl border border-secondary/60 bg-secondary/15 p-4" key={item.id}><div className="flex items-start gap-3"><span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary text-secondary"><Megaphone className="size-4" aria-hidden /></span><div className="min-w-0"><h2 className="text-base font-bold">{item.title}</h2><p className="mt-1 text-sm leading-6 text-muted-foreground">{item.message}</p></div></div></article>)}</section> : null}
    {data.membership ? <>
      <div className="grid gap-5 lg:grid-cols-[1.3fr_0.7fr]">
        {data.crowdedness ? <OccupancyCard data={data.crowdedness} /> : null}
        <EmbeddedQr eligible={data.qr_access.eligible} reason={data.qr_access.reason} />
      </div>
      <TrafficHistory query={traffic} />
    </> : <section className="rounded-2xl border border-border bg-card p-6"><h2 className="text-xl font-bold">Choose your gym</h2><p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">Buy a membership and pick a location to see live occupancy, quiet times and your check-in code.</p><Link className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground" to="/memberships">Buy membership <ArrowRight className="size-4" aria-hidden /></Link></section>}
    {data.membership ? <section className="rounded-2xl border border-border bg-card p-5" aria-labelledby="membership-heading"><div className="flex flex-wrap items-center justify-between gap-3"><h2 id="membership-heading" className="text-lg font-bold">Membership</h2><StatusBadge value={data.membership.status} /></div><p className="mt-3 text-sm"><strong>{data.membership.plan_name}</strong> · {data.membership.days_remaining} days remaining · expires {formatDate(data.membership.expiry_date)}</p><p className="mt-1 text-xs text-muted-foreground">{data.membership.message}</p><Link className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-primary" to="/memberships">Renew membership<ArrowRight className="size-4" aria-hidden /></Link></section> : null}
    <section className="grid gap-5 lg:grid-cols-2"><article className="rounded-2xl border border-border bg-card p-5"><div className="flex items-center justify-between"><div><h2 className="text-lg font-bold">Upcoming bookings</h2><p className="mt-1 text-xs text-muted-foreground">Your next three confirmed classes.</p></div><Link className="text-sm font-bold text-primary" to="/app/bookings">View all</Link></div>{data.upcoming_bookings.length ? <ul className="mt-4 grid gap-3">{data.upcoming_bookings.map((booking) => <li className="rounded-xl bg-muted/50 p-4" key={booking.id}><div className="flex items-start justify-between gap-3"><div className="min-w-0"><strong>{booking.gym_class.title}</strong><p className="mt-1 text-xs text-muted-foreground">{formatDateTime(booking.gym_class.start_at)} / {booking.gym_class.location}</p></div><StatusBadge value={booking.status} /></div></li>)}</ul> : <EmptyState className="mt-4" title="No upcoming bookings" message="Book a class to see it here." />}{data.active_waitlists.length ? <div className="mt-5 border-t border-border pt-4"><p className="text-xs font-black uppercase tracking-wider text-muted-foreground">Active waitlists</p>{data.active_waitlists.map((entry) => <p className="mt-2 text-sm" key={entry.id}>{entry.gym_class.title} / position {entry.position}</p>)}</div> : null}</article>
      <article className="rounded-2xl border border-border bg-card p-5"><div className="flex items-center justify-between"><div><h2 className="text-lg font-bold">Notifications</h2><p className="mt-1 text-xs text-muted-foreground">{data.unread_notification_count} unread</p></div><Bell className="size-5 text-primary" aria-hidden /></div>{notifications.length ? <ul className="mt-4 grid gap-3">{notifications.map((item) => <li className="rounded-xl border border-border p-4" key={item.id}><strong className="text-sm">{item.title}</strong><p className="mt-1 text-xs leading-5 text-muted-foreground">{item.message}</p></li>)}</ul> : <EmptyState className="mt-4" title="No notifications" message="Booking and membership updates will appear here." />}<Link className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-primary" to="/app/notifications">Open inbox <ArrowRight className="size-4" aria-hidden /></Link></article>
    </section>
    <section className="rounded-2xl border border-border bg-card p-5"><h2 className="text-lg font-bold">Quick actions</h2><div className="mt-4 grid gap-3 sm:grid-cols-3">{visibleQuickActions(data.quick_actions).map((action) => { const Icon = actionIcons[action.key as keyof typeof actionIcons] ?? Dumbbell; return action.enabled ? <Link className="rounded-xl border border-border p-4 transition hover:-translate-y-0.5 hover:bg-muted" to={action.target} key={action.key}><Icon className="size-5 text-primary" aria-hidden /><strong className="mt-3 block text-sm">{action.label}</strong></Link> : <div className="rounded-xl border border-border bg-muted/40 p-4 text-muted-foreground" aria-disabled="true" title={action.reason ?? undefined} key={action.key}><Icon className="size-5" aria-hidden /><strong className="mt-3 block text-sm">{action.label}</strong><span className="mt-1 block text-xs">Unavailable</span></div>; })}</div></section>
  </div></MemberShell>;
}

function DashboardSkeleton() { return <div className="mx-auto max-w-6xl animate-pulse" role="status" aria-label="Loading member dashboard"><div className="h-16 rounded-2xl bg-muted" /><div className="mt-5 grid gap-5 lg:grid-cols-[1.3fr_0.7fr]"><div className="h-56 rounded-2xl bg-muted" /><div className="h-56 rounded-2xl bg-muted" /></div><div className="mt-5 h-64 rounded-2xl bg-muted" /><span className="sr-only">Loading member dashboard</span></div>; }
