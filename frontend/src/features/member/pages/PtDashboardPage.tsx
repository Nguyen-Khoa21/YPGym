import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock3 } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { Modal, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { PTCard } from "@/features/classes/components/PTCard";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import { refreshManagementQueries } from "@/lib/managementMutations";
import type { GymClass, Trainer } from "@/types/operations";

export function PtDashboardPage() {
  const { token, user } = useAuth();
  const queryClient = useQueryClient();
  const [selectedClass, setSelectedClass] = useState<GymClass | null>(null);
  const trainer = useQuery({
    queryKey: ["trainer", "me", user?.id],
    queryFn: ({ signal }) => apiRequest<Trainer>("/trainers/me", { token, signal }),
  });
  const startedClasses = useQuery({
    queryKey: ["trainer", "me", "classes", user?.id],
    queryFn: ({ signal }) => apiRequest<GymClass[]>("/trainers/me/classes", { token, signal }),
  });
  const completeClass = useMutation({
    mutationFn: (classId: string) => apiRequest<GymClass>(`/trainers/me/classes/${classId}/complete`, {
      method: "POST",
      token,
    }),
    onSuccess: async () => {
      setSelectedClass(null);
      await refreshManagementQueries(queryClient, "classes");
      toast.success("Class marked as completed");
    },
    onError: (error) => toast.error(toUiError(error).message),
  });

  return <AppFrame>
    <main id="main-content" className="mx-auto min-h-[calc(100vh-4.8rem)] max-w-5xl px-5 py-10 sm:px-8">
      <p className="page-kicker">PT workspace</p>
      <h1 className="page-title">Welcome back, {user?.name}.</h1>
      <p className="page-description">Review your trainer profile, upcoming assignments, and confirm classes you have delivered.</p>

      {trainer.isLoading ? <LoadingState className="mt-6" title="Loading your trainer profile" /> : null}
      {trainer.isError ? <ErrorState className="mt-6" title={toUiError(trainer.error).title} message={toUiError(trainer.error).message} action={<Button variant="outline" onClick={() => void trainer.refetch()}>Retry</Button>} /> : null}

      <div className="mt-6 grid items-start gap-5 md:grid-cols-2">
        {trainer.data ? <section aria-label="Your trainer profile">
          <div className="mb-3"><StatusBadge value={trainer.data.is_active ? "active" : "inactive"} /></div>
          <PTCard trainer={trainer.data} />
          {trainer.data.upcoming_classes.length === 0 ? <EmptyState className="mt-4" title="No upcoming assignments" message="Your next scheduled classes will appear here after assignment." /> : null}
        </section> : null}
        <section className="surface-card p-6">
          <h2 className="text-xl font-bold">Your account</h2>
          <p className="mt-3 break-words text-sm text-muted-foreground">{user?.email}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Link to="/staff/time-clock" className="inline-flex rounded-full bg-primary px-5 py-3 text-sm font-extrabold text-primary-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">Open time clock</Link>
            <Link to="/app/profile" className="inline-flex rounded-full border border-border px-5 py-3 text-sm font-extrabold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">Edit account details</Link>
          </div>
        </section>
      </div>

      <Panel className="mt-6" title="Classes ready for confirmation" detail="Only classes assigned to you appear here after their start time. Classes also complete automatically after their end time.">
        {startedClasses.isLoading ? <LoadingState className="m-4" title="Loading started classes" /> : null}
        {startedClasses.isError ? <ErrorState className="m-4" title={toUiError(startedClasses.error).title} message={toUiError(startedClasses.error).message} action={<Button variant="outline" onClick={() => void startedClasses.refetch()}>Retry</Button>} /> : null}
        {startedClasses.data?.length === 0 ? <EmptyState className="m-4" title="No classes need confirmation" message="An assigned class will appear here after it starts and disappear once it is completed or cancelled." /> : null}
        {startedClasses.data?.length ? <ul className="grid gap-3 p-4 sm:grid-cols-2">
          {startedClasses.data.map((item) => {
            const hasEnded = new Date(item.end_at).getTime() <= Date.now();
            return <li className="rounded-xl border border-border p-4" key={item.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <strong className="block">{item.title}</strong>
                  <p className="mt-1 text-xs text-muted-foreground">{item.location}</p>
                </div>
                <StatusBadge value={hasEnded ? "ended" : "in progress"} />
              </div>
              <p className="mt-4 flex items-center gap-2 text-sm text-muted-foreground"><Clock3 className="size-4" aria-hidden />{formatDateTime(item.start_at)} to {new Date(item.end_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p>
              <Button className="mt-4 w-full" onClick={() => setSelectedClass(item)}><CheckCircle2 className="size-4" aria-hidden />Confirm completed</Button>
            </li>;
          })}
        </ul> : null}
      </Panel>

      {selectedClass ? <Modal
        title={`Complete ${selectedClass.title}?`}
        description="This records a final completed status and cannot be reversed. Only confirm after you have delivered the class."
        error={completeClass.isError ? toUiError(completeClass.error).message : undefined}
        onClose={() => { if (!completeClass.isPending) setSelectedClass(null); }}
      >
        <div className="ops-modal__body">
          <p className="text-sm text-muted-foreground">Scheduled for {formatDateTime(selectedClass.start_at)} at {selectedClass.location}.</p>
          <div className="ops-modal__actions">
            <Button variant="outline" disabled={completeClass.isPending} onClick={() => setSelectedClass(null)}>Keep scheduled</Button>
            <Button disabled={completeClass.isPending} onClick={() => completeClass.mutate(selectedClass.id)}>{completeClass.isPending ? "Completing..." : "Confirm completed"}</Button>
          </div>
        </div>
      </Modal> : null}
    </main>
  </AppFrame>;
}
