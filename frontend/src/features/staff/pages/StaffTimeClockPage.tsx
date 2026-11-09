import { useMutation, useQuery } from "@tanstack/react-query";
import { Clock3, LogIn, LogOut, UserPlus } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { workforceNavigationForRole } from "@/app/navigation";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { AttendanceSessionsPanel } from "@/features/attendance/components/AttendanceSessionsPanel";
import { OccupancyMetrics } from "@/features/attendance/components/OccupancyMetrics";
import { gymMarker } from "@/features/operations/gymScope";
import { useOperationsScope } from "@/features/operations/useOperationsScope";
import { InPersonRegistrationDialog } from "@/features/staff/components/InPersonRegistrationDialog";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { Crowdedness, MyStaffShifts, StaffShift } from "@/types/operations";

function durationLabel(minutes: number) {
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export function StaffTimeClockPage() {
  const { token, user } = useAuth();
  const query = useQuery({
    queryKey: ["staff", "shifts", "me", user?.id],
    queryFn: ({ signal }) => apiRequest<MyStaffShifts>("/staff/shifts/me", { token, signal }),
  });
  const clock = useMutation({
    mutationFn: (action: "clock-in" | "clock-out") => apiRequest<StaffShift>(`/staff/shifts/${action}`, { method: "POST", token }),
    onSuccess: async (_, action) => {
      await queryClient.invalidateQueries({ queryKey: ["staff", "shifts"] });
      queryClient.removeQueries({ queryKey: ["attendance"] });
      toast.success(action === "clock-in" ? "Clocked in" : "Clocked out");
    },
    onError: (error) => toast.error(toUiError(error).message),
  });
  const nav = workforceNavigationForRole(user?.role);

  return <AppFrame navigation={nav}><main id="main-content" className="mx-auto min-h-[calc(100vh-4.8rem)] max-w-5xl px-5 py-10 sm:px-8">
    <p className="page-kicker">Workforce operations</p><h1 className="page-title">{user?.role === "staff" ? "Staff workspace." : "Staff time clock."}</h1><p className="page-description">Server timestamps are authoritative. Times below use the configured gym timezone.</p>
    {query.isLoading ? <LoadingState className="mt-6" title="Loading your shifts" /> : null}
    {query.isError ? <ErrorState className="mt-6" title={toUiError(query.error).title} message={toUiError(query.error).message} action={<Button variant="outline" onClick={() => void query.refetch()}>Retry</Button>} /> : null}
    {query.data ? <div className="mt-7 grid items-start gap-5 lg:grid-cols-[0.8fr_1.2fr]">
      <section className="rounded-2xl bg-primary p-6 text-primary-foreground"><span className="grid size-11 place-items-center rounded-xl bg-secondary text-foreground"><Clock3 className="size-5" aria-hidden /></span><p className="mt-6 text-xs font-black uppercase tracking-wider text-secondary">Current status</p><h2 className="mt-2 font-['Barlow_Condensed'] text-4xl font-bold uppercase">{query.data.open_shift ? "Clocked in" : "Clocked out"}</h2>{query.data.open_shift ? <p className="mt-3 text-sm text-primary-foreground/75">Started {formatDateTime(query.data.open_shift.clocked_in_at, query.data.gym_timezone)}</p> : <p className="mt-3 text-sm text-primary-foreground/75">No open shift. Clock in when your work begins.</p>}<Button className="mt-6 w-full" variant="secondary" disabled={clock.isPending} onClick={() => clock.mutate(query.data.open_shift ? "clock-out" : "clock-in")}>{query.data.open_shift ? <><LogOut className="size-4" /> Clock out</> : <><LogIn className="size-4" /> Clock in</>}</Button></section>
      <Panel title="Recent shifts" detail={`Displayed in ${query.data.gym_timezone}`}>
        {query.data.recent_shifts.length === 0 ? <EmptyState className="m-4" title="No shifts yet" message="Your first clock-in will create an auditable shift." /> : <div className="divide-y divide-border">{query.data.recent_shifts.map((shift) => <article className="flex flex-wrap items-start justify-between gap-4 p-4" key={shift.id}><div><strong className="text-sm">{formatDateTime(shift.clocked_in_at, query.data.gym_timezone)}</strong><p className="mt-1 text-xs text-muted-foreground">{shift.clocked_out_at ? `Ended ${formatDateTime(shift.clocked_out_at, query.data.gym_timezone)}` : "Currently open"} · {durationLabel(shift.duration_minutes)}</p></div><StatusBadge value={shift.status} /></article>)}</div>}
      </Panel>
    </div> : null}
    {user?.role === "staff" && query.data ? <StaffWorkspacePanels shiftOpen={Boolean(query.data.open_shift)} onShiftLost={() => void query.refetch()} clockIn={() => clock.mutate("clock-in")} clocking={clock.isPending} /> : null}
  </main></AppFrame>;
}

/** Attendance, live capacity and walk-in registration. Nothing is requested until the shift is open. */
function StaffWorkspacePanels({ shiftOpen, onShiftLost, clockIn, clocking }: { shiftOpen: boolean; onShiftLost: () => void; clockIn: () => void; clocking: boolean }) {
  const { token } = useAuth();
  const scope = useOperationsScope();
  const [registering, setRegistering] = useState(false);
  const unlocked = scope.ready && shiftOpen;
  const crowdedness = useQuery({
    queryKey: ["attendance", "crowdedness", gymMarker(scope.gymId)],
    queryFn: ({ signal }) => apiRequest<Crowdedness>("/attendance/crowdedness", { token, signal }),
    refetchInterval: 30_000,
    enabled: unlocked && Boolean(scope.gymId),
  });
  const shiftRequired = useCallback(() => onShiftLost(), [onShiftLost]);
  return <section className="mt-9" aria-label="Gym workspace">
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div><p className="page-kicker">Your gym</p><h2 className="font-['Barlow_Condensed'] text-3xl font-bold uppercase">{scope.gymName ?? "Loading your gym"}</h2></div>
      {unlocked ? <Button onClick={() => setRegistering(true)}><UserPlus className="size-4" aria-hidden />Register new member</Button> : null}
    </div>
    {scope.error ? <ErrorState className="mb-5" title={toUiError(scope.error).title} message={toUiError(scope.error).message} action={<Button variant="outline" onClick={scope.retry}>Retry</Button>} /> : null}
    {!shiftOpen ? <Panel title="Clock in to start" detail="Attendance, live capacity and member registration open only while you are on shift.">
      <div className="p-5"><p className="text-sm text-muted-foreground">No attendance or occupancy data is loaded until you clock in.</p><Button className="mt-4" disabled={clocking} onClick={clockIn}><LogIn className="size-4" aria-hidden />Clock in</Button></div>
    </Panel> : <>
      <OccupancyMetrics crowdedness={crowdedness} gymId={scope.gymId}><></></OccupancyMetrics>
      <AttendanceSessionsPanel scope={scope} enabled={unlocked} onShiftRequired={shiftRequired} />
    </>}
    {registering ? <InPersonRegistrationDialog scope={scope} onClose={() => setRegistering(false)} /> : null}
  </section>;
}
