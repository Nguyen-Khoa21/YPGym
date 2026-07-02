import { Dumbbell } from "lucide-react";

import { EmptyState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";

export function PtDashboardPage() {
  return (
    <AppFrame>
      <main className="mx-auto max-w-4xl px-5 py-10">
        <Dumbbell className="size-8 text-primary" aria-hidden />
        <h1 className="mt-4 text-3xl font-bold">PT Dashboard</h1>
        <p className="mt-2 text-muted-foreground">
          A safe role destination for personal trainers after login.
        </p>
        <EmptyState
          className="mt-6"
          title="Trainer schedule starts later"
          message="PT assignments and class tooling are outside Day 11-20."
        />
      </main>
    </AppFrame>
  );
}
