import type { UseQueryResult } from "@tanstack/react-query";
import type { PropsWithChildren } from "react";

import { ErrorState } from "@/components/common/FeedbackState";
import { MetricCard } from "@/components/operations/OperationsUi";
import { toUiError } from "@/lib/apiErrors";
import type { Crowdedness } from "@/types/operations";

/** Live occupancy for one gym. Shared by the manager attendance page and the staff workspace. */
export function OccupancyMetrics({
  crowdedness,
  gymId,
  children,
}: PropsWithChildren<{ crowdedness: UseQueryResult<Crowdedness>; gymId: string }>) {
  return (
    <>
      <div className="ops-metrics">
        <MetricCard
          label="Active occupancy"
          value={crowdedness.data?.active_count ?? "-"}
          tone="forest"
          detail={
            crowdedness.data
              ? `${crowdedness.data.capacity} capacity`
              : gymId
                ? "Loading facility count"
                : "Choose a branch"
          }
        />
        <MetricCard
          label="Capacity used"
          value={crowdedness.data ? `${crowdedness.data.percentage}%` : "-"}
          tone="lime"
        />
        <MetricCard label="Facility status" value={crowdedness.data?.status ?? "Checking"} />
        {children}
      </div>
      {crowdedness.isError ? (
        <ErrorState
          className="mb-5"
          title={toUiError(crowdedness.error).title}
          message={toUiError(crowdedness.error).message}
        />
      ) : null}
    </>
  );
}
