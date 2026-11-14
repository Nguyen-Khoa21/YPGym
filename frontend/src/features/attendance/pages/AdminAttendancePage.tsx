import { useCallback, useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Activity, Clock3, LogIn, LogOut, ShieldCheck, UsersRound } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { AttendanceSessionsPanel } from "@/features/attendance/components/AttendanceSessionsPanel";
import { OccupancyMetrics } from "@/features/attendance/components/OccupancyMetrics";
import { MetricCard, OperationsHeader, Panel } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { GymScopeBar } from "@/features/operations/components/GymScopeBar";
import { gymMarker } from "@/features/operations/gymScope";
import { useOperationsScope } from "@/features/operations/useOperationsScope";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime, formatMoney } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type {
  AnalyticsSummary,
  Crowdedness,
  MyStaffShifts,
  StaffShift,
  TrafficSummary,
} from "@/types/operations";

export function AdminAttendancePage() {
  const { token, user } = useAuth();
  const scope = useOperationsScope();
  const isStaff = user?.role === "staff";
  const shift = useQuery({
    queryKey: ["staff", "shifts", "me", user?.id],
    queryFn: ({ signal }) => apiRequest<MyStaffShifts>("/staff/shifts/me", { token, signal }),
    enabled: isStaff,
  });
  const marker = gymMarker(scope.gymId);
  const gymQuery = scope.gymParam ? `?gym_id=${encodeURIComponent(scope.gymParam)}` : "";
  const canViewAnalytics = user?.role === "manager" || user?.role === "admin";
  const shiftOpen = !isStaff || Boolean(shift.data?.open_shift);
  const [shiftRejected, setShiftRejected] = useState(false);
  const markShiftRejected = useCallback(() => setShiftRejected(true), []);
  // Staff may only use attendance while clocked in. Nothing is requested while locked.
  const unlocked = scope.ready && shiftOpen && !shiftRejected;
  const crowdedness = useQuery({
    queryKey: ["attendance", "crowdedness", marker],
    queryFn: ({ signal }) =>
      apiRequest<Crowdedness>(`/attendance/crowdedness${gymQuery}`, { token, signal }),
    refetchInterval: 30_000,
    enabled: unlocked && Boolean(scope.gymId),
  });
  const traffic = useQuery({
    queryKey: ["attendance", "traffic-summary", marker],
    queryFn: ({ signal }) =>
      apiRequest<TrafficSummary>(`/admin/analytics/traffic-summary${gymQuery}`, { token, signal }),
    enabled: canViewAnalytics && unlocked && Boolean(scope.gymId),
    staleTime: 300_000,
  });
  const summary = useQuery({
    queryKey: ["attendance", "analytics-summary", marker],
    queryFn: ({ signal }) =>
      apiRequest<AnalyticsSummary>(`/admin/analytics/summary${gymQuery}`, { token, signal }),
    enabled: canViewAnalytics && unlocked,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
  const shiftRefetch = shift.refetch;
  useEffect(() => {
    if (shiftRejected) void shiftRefetch();
  }, [shiftRejected, shiftRefetch]);
  const clock = useMutation({
    mutationFn: (action: "clock-in" | "clock-out") =>
      apiRequest<StaffShift>(`/staff/shifts/${action}`, { method: "POST", token }),
    onSuccess: async (_, action) => {
      setShiftRejected(false);
      // Update the shift first so the workspace locks before cached attendance data is discarded.
      await queryClient.invalidateQueries({ queryKey: ["staff", "shifts"] });
      queryClient.removeQueries({ queryKey: ["attendance", "admin"] });
      toast.success(action === "clock-in" ? "Clocked in" : "Clocked out");
    },
    onError: (error) => toast.error(toUiError(error).message),
  });
  if (isStaff && shift.isLoading)
    return (
      <AdminShell>
        <LoadingState className="m-4" title="Checking your shift" />
      </AdminShell>
    );
  if (isStaff && (!shiftOpen || shiftRejected))
    return (
      <AdminShell>
        <div className="mx-auto max-w-3xl">
          <OperationsHeader
            kicker="Attendance operations"
            title="Clock in to start."
            description="Attendance tools open only while you are on shift at your gym."
          />
          <GymScopeBar scope={scope} />
          <Panel
            title="You are clocked out"
            detail={scope.gymName ? `Gym: ${scope.gymName}` : "Loading your gym"}
          >
            <div className="p-5">
              <p className="text-sm text-muted-foreground">
                No attendance or occupancy data is loaded until you clock in.
              </p>
              <Button
                className="mt-4"
                disabled={clock.isPending}
                onClick={() => clock.mutate("clock-in")}
              >
                <LogIn className="size-4" /> Clock in
              </Button>
              {shift.isError ? (
                <p className="mt-3 text-sm text-destructive">{toUiError(shift.error).message}</p>
              ) : null}
            </div>
          </Panel>
        </div>
      </AdminShell>
    );
  return (
    <AdminShell>
      <div className="mx-auto max-w-7xl">
        <OperationsHeader
          kicker="Attendance operations"
          title="Live occupancy, permanent evidence."
          description="The dashboard combines current capacity, persisted sessions, closure controls, and previous-month occupancy estimates."
          actions={
            isStaff && shift.data?.open_shift ? (
              <Button
                variant="outline"
                disabled={clock.isPending}
                onClick={() => clock.mutate("clock-out")}
              >
                <LogOut className="size-4" /> Clock out
              </Button>
            ) : undefined
          }
        />
        <GymScopeBar scope={scope} />
        {isStaff && shift.data?.open_shift ? (
          <p className="mb-4 text-sm text-muted-foreground">
            On shift since{" "}
            {formatDateTime(shift.data.open_shift.clocked_in_at, shift.data.gym_timezone)}.
          </p>
        ) : null}
        {scope.error ? (
          <ErrorState
            className="mb-5"
            title={toUiError(scope.error).title}
            message={toUiError(scope.error).message}
            action={
              <Button variant="outline" onClick={scope.retry}>
                Retry
              </Button>
            }
          />
        ) : null}
        {scope.isOwner && scope.ready && !scope.gymId ? (
          <p className="mb-4 rounded-lg border border-border bg-muted/50 p-3 text-sm">
            Showing all branches. Choose one branch to see its live occupancy and traffic.
            Percentages of different gyms are never combined.
          </p>
        ) : null}
        <OccupancyMetrics crowdedness={crowdedness} gymId={scope.gymId}>
          <MetricCard
            label="Previous-month visits"
            value={traffic.data?.visits ?? "Role restricted"}
            tone="coral"
            detail={
              traffic.data?.data_sufficient
                ? `${traffic.data.unique_members} unique members`
                : "Manager/admin analytics"
            }
          />
        </OccupancyMetrics>
        <AttendanceSessionsPanel
          scope={scope}
          enabled={unlocked}
          onShiftRequired={markShiftRejected}
        />
        <div className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
          <Panel
            title="Previous-month traffic"
            detail={
              canViewAnalytics
                ? "Average concurrent occupancy sampled every 15 minutes and grouped into two-hour local-time windows."
                : "Manager/admin analytics are intentionally hidden from staff."
            }
          >
            <TrafficPanel query={traffic} canView={canViewAnalytics} />
          </Panel>
          <Panel title="Control boundaries" detail="Role-aware operational safeguards.">
            <div className="grid gap-3 p-4">
              <Control
                icon={UsersRound}
                title="Member isolation"
                detail="Members can retrieve only their own attendance history."
              />
              <Control
                icon={ShieldCheck}
                title="Reason required"
                detail="Staff, managers, and admins can close abnormal active sessions only with an audit reason."
              />
              <Control
                icon={Clock3}
                title="Timeout worker"
                detail="Celery Beat reconciles sessions older than the configured timeout."
              />
              <Control
                icon={Activity}
                title="Database truth"
                detail="Occupancy is rebuilt from active PostgreSQL sessions when the cache is absent or stale."
              />
            </div>
          </Panel>
        </div>
        {canViewAnalytics ? <AnalyticsSummaryPanel query={summary} /> : null}
      </div>
    </AdminShell>
  );
}

function AnalyticsSummaryPanel({
  query,
}: {
  query: ReturnType<typeof useQuery<AnalyticsSummary>>;
}) {
  if (query.isLoading)
    return (
      <Panel
        className="mt-5"
        title="Manager summary"
        detail="Membership, class, attendance, and revenue aggregates are calculated from persisted records."
      >
        <LoadingState className="m-4" title="Aggregating manager summary" />
      </Panel>
    );
  if (query.isError)
    return (
      <Panel
        className="mt-5"
        title="Manager summary"
        detail="The analytics summary could not be loaded."
      >
        <ErrorState
          className="m-4"
          title={toUiError(query.error).title}
          message={toUiError(query.error).message}
          action={
            <Button variant="outline" onClick={() => query.refetch()}>
              Retry
            </Button>
          }
        />
      </Panel>
    );
  if (!query.data) return null;
  const data = query.data;
  return (
    <Panel
      className="mt-5"
      title="Manager summary"
      detail={`Last 30 days through ${formatDateTime(data.date_to)}. Checks for updates every minute; generated ${formatDateTime(data.generated_at)}.`}
    >
      <div className="ops-metrics p-4">
        {data.revenue ? (
          <MetricCard
            label="Successful payments"
            value={data.revenue.successful_payments}
            tone="coral"
            detail={formatMoney(data.revenue.gross_amount)}
          />
        ) : (
          <MetricCard
            label="Class bookings"
            value={data.class_popularity.reduce((total, item) => total + item.bookings, 0)}
            tone="coral"
            detail="Last 30 days, this gym"
          />
        )}
        <MetricCard
          label="Check-ins"
          value={data.attendance.check_ins}
          tone="forest"
          detail={`${data.attendance.unique_members} unique members`}
        />
        <MetricCard
          label="Average visit"
          value={
            data.attendance.average_visit_minutes === null
              ? "-"
              : `${data.attendance.average_visit_minutes} min`
          }
          tone="lime"
          detail={data.attendance.busiest_slot ?? "No peak slot"}
        />
        {data.revenue ? (
          <MetricCard label="Discounts" value={formatMoney(data.revenue.discounts)} />
        ) : (
          <MetricCard
            label="Memberships created"
            value={data.membership_trends.reduce((total, item) => total + item.total, 0)}
            detail="Last 30 days, this gym"
          />
        )}
      </div>
      <div className="grid gap-5 border-t border-border p-4 xl:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold">Memberships created by month (UTC)</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Current status of memberships created in each month; renewals update the existing
            membership.
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="pb-2">Month</th>
                  <th className="pb-2">Total</th>
                  <th className="pb-2">Active</th>
                  <th className="pb-2">Frozen</th>
                  <th className="pb-2">Expired</th>
                </tr>
              </thead>
              <tbody>
                {data.membership_trends.map((point) => (
                  <tr className="border-b border-border/60" key={point.period}>
                    <td className="py-2">
                      {new Intl.DateTimeFormat("en-MY", {
                        month: "short",
                        year: "numeric",
                        timeZone: "UTC",
                      }).format(new Date(`${point.period}T00:00:00Z`))}
                    </td>
                    <td>{point.total}</td>
                    <td>{point.active}</td>
                    <td>{point.frozen}</td>
                    <td>{point.expired}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h3 className="text-sm font-semibold">Class popularity</h3>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="pb-2">Type</th>
                  <th className="pb-2">Bookings</th>
                  <th className="pb-2">Unique members</th>
                  <th className="pb-2">Use</th>
                </tr>
              </thead>
              <tbody>
                {data.class_popularity.map((point) => (
                  <tr className="border-b border-border/60" key={point.class_type}>
                    <td className="py-2">{point.class_type}</td>
                    <td>{point.bookings}</td>
                    <td>{point.unique_members}</td>
                    <td>{point.utilization_percent}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.class_popularity.length === 0 ? (
              <p className="mt-3 text-xs text-muted-foreground">
                No classes were scheduled in this range.
              </p>
            ) : null}
          </div>
        </div>
      </div>
    </Panel>
  );
}

function TrafficPanel({
  query,
  canView,
}: {
  query: ReturnType<typeof useQuery<TrafficSummary>>;
  canView: boolean;
}) {
  if (!canView)
    return (
      <EmptyState
        className="m-4"
        title="Operational access only"
        message="Staff can manage attendance sessions but cannot view manager analytics."
      />
    );
  if (query.isLoading)
    return <LoadingState className="m-4" title="Estimating previous-month occupancy" />;
  if (query.isError)
    return (
      <ErrorState
        className="m-4"
        title={toUiError(query.error).title}
        message={toUiError(query.error).message}
        action={
          <Button variant="outline" onClick={() => query.refetch()}>
            Retry
          </Button>
        }
      />
    );
  if (!query.data) return null;
  const data = query.data;
  if (!data.data_sufficient)
    return (
      <EmptyState
        className="m-4"
        title="Not enough attendance data yet"
        message={`At least ${data.methodology.minimum_sessions} overlapping sessions are required before busiest or quietest windows are shown.`}
      />
    );
  return (
    <div>
      <div className="ops-metrics p-4">
        <MetricCard
          label="Busiest window"
          value={data.busiest_window?.label ?? "-"}
          tone="coral"
          detail={
            data.busiest_window
              ? `${data.busiest_window.average_capacity_percentage}% average capacity`
              : undefined
          }
        />
        <MetricCard
          label="Quietest window"
          value={data.quietest_window?.label ?? "-"}
          tone="lime"
          detail={
            data.quietest_window
              ? `${data.quietest_window.average_capacity_percentage}% average capacity`
              : undefined
          }
        />
        <MetricCard
          label="Average occupancy"
          value={`${data.average_capacity_percentage}%`}
          tone="forest"
          detail={`${data.average_headcount} average members`}
        />
        <MetricCard
          label="Average visit"
          value={data.average_visit_minutes === null ? "-" : `${data.average_visit_minutes} min`}
          detail={`${data.visits} visits · ${data.unique_members} members`}
        />
      </div>
      {data.contains_demo_data ? (
        <p className="mx-4 mb-3 rounded-lg border border-secondary/50 bg-secondary/10 p-3 text-xs font-semibold">
          This summary includes synthetic demo attendance.
        </p>
      ) : null}
      <TrafficHeatmap data={data} />
      <p className="px-4 pb-4 text-xs leading-5 text-muted-foreground">
        Historical estimate, not a prediction. The previous completed month uses {data.timezone},{" "}
        {data.methodology.sample_interval_minutes}-minute samples, and two-hour windows.{" "}
        {data.methodology.session_end_rule}
      </p>
    </div>
  );
}

function TrafficHeatmap({ data }: { data: TrafficSummary }) {
  const maximum = Math.max(
    0,
    ...data.weekday_buckets.map((cell) => cell.average_capacity_percentage),
  );
  const rows = Array.from({ length: 7 }, (_, weekday) =>
    data.weekday_buckets.filter((cell) => cell.weekday === weekday),
  );
  return (
    <div className="heatmap-wrap">
      <div
        className="attendance-heatmap attendance-heatmap--traffic"
        role="grid"
        aria-label="Previous-month average occupancy heatmap"
      >
        <div className="heatmap-row heatmap-row--header" role="row">
          <span role="columnheader">Day</span>
          {data.buckets.map((bucket) => (
            <span role="columnheader" key={bucket.start_hour}>
              {bucket.start_hour.toString().padStart(2, "0")}
            </span>
          ))}
        </div>
        {rows.map((row, weekday) => (
          <div className="heatmap-row" role="row" key={weekday}>
            <strong role="rowheader">{row[0]?.weekday_label.slice(0, 3)}</strong>
            {row.map((cell) => {
              const intensity = maximum ? cell.average_capacity_percentage / maximum : 0;
              const tone =
                cell.average_capacity_percentage === 0
                  ? "empty"
                  : intensity <= 0.33
                    ? "low"
                    : intensity <= 0.66
                      ? "medium"
                      : "high";
              const description = `${cell.weekday_label}, ${cell.label}: ${cell.average_headcount} average members, ${cell.average_capacity_percentage}% capacity`;
              return (
                <span
                  className={`heatmap-cell heatmap-cell--${tone}`}
                  role="gridcell"
                  aria-label={description}
                  title={description}
                  key={cell.start_hour}
                >
                  {cell.average_capacity_percentage}%
                </span>
              );
            })}
          </div>
        ))}
      </div>
      <div className="overflow-x-auto px-4 pb-4">
        <table className="w-full text-left text-xs">
          <caption className="sr-only">Two-hour average occupancy text alternative</caption>
          <thead>
            <tr className="border-b border-border text-muted-foreground">
              <th className="pb-2">Window</th>
              <th className="pb-2">Average members</th>
              <th className="pb-2">Capacity used</th>
            </tr>
          </thead>
          <tbody>
            {data.buckets.map((bucket) => (
              <tr className="border-b border-border/60" key={bucket.start_hour}>
                <td className="py-2">{bucket.label}</td>
                <td>{bucket.average_headcount}</td>
                <td>{bucket.average_capacity_percentage}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Control({
  icon: Icon,
  title,
  detail,
}: {
  icon: typeof Activity;
  title: string;
  detail: string;
}) {
  return (
    <article className="rounded-xl border border-border p-4">
      <Icon className="size-5 text-primary" />
      <strong className="mt-3 block text-sm">{title}</strong>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
    </article>
  );
}
