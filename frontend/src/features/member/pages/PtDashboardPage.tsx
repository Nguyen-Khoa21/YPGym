import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { PTCard } from "@/features/classes/components/PTCard";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import type { Trainer } from "@/types/operations";

export function PtDashboardPage() {
  const { token, user } = useAuth();
  const trainer = useQuery({ queryKey: ["trainer", "me", user?.id], queryFn: ({ signal }) => apiRequest<Trainer>("/trainers/me", { token, signal }) });
  return <AppFrame>
    <main id="main-content" className="mx-auto min-h-[calc(100vh-4.8rem)] max-w-5xl px-5 py-10 sm:px-8">
      <p className="page-kicker">PT workspace</p><h1 className="page-title">Welcome back, {user?.name}.</h1>
      <p className="page-description">Your trainer profile and next three scheduled classes. Managers maintain trainer details and class assignments.</p>
      {trainer.isLoading ? <LoadingState className="mt-6" title="Loading your trainer profile" /> : null}
      {trainer.isError ? <ErrorState className="mt-6" title={toUiError(trainer.error).title} message={toUiError(trainer.error).message} action={<Button variant="outline" onClick={() => void trainer.refetch()}>Retry</Button>} /> : null}
      <div className="mt-6 grid items-start gap-5 md:grid-cols-2">
        {trainer.data ? <section aria-label="Your trainer profile"><div className="mb-3"><StatusBadge value={trainer.data.is_active ? "active" : "inactive"} /></div><PTCard trainer={trainer.data} />{trainer.data.upcoming_classes.length === 0 ? <EmptyState className="mt-4" title="No upcoming assignments" message="Your next scheduled classes will appear here after assignment." /> : null}</section> : null}
        <section className="surface-card p-6"><h2 className="text-xl font-bold">Your account</h2><p className="mt-3 break-words text-sm text-muted-foreground">{user?.email}</p><Link to="/app/profile" className="mt-5 inline-flex rounded-full bg-primary px-5 py-3 text-sm font-extrabold text-primary-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">Edit account details</Link></section>
      </div>
    </main>
  </AppFrame>;
}
