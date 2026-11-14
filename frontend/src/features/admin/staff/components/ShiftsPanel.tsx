import type { UseQueryResult } from "@tanstack/react-query";

import { QueryState } from "@/components/common/QueryState";
import { Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { formatDateTime } from "@/lib/format";
import type { StaffShiftPage } from "@/types/operations";

type Props = {
  query: UseQueryResult<StaffShiftPage>;
  page: number;
  onPage: (page: number) => void;
};

function durationLabel(minutes: number) {
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export function ShiftsPanel({ query, page, onPage }: Props) {
  return (
    <Panel
      title="Shift report"
      detail={
        query.data
          ? `Displayed in ${query.data.gym_timezone}`
          : "UTC records rendered in gym local time."
      }
    >
      <QueryState
        query={query}
        className="m-4"
        loading={{ title: "Loading shifts" }}
        retry
        empty={{
          title: "No matching shifts",
          message: "Shift records appear after staff or PT users clock in.",
        }}
        isEmpty={(data) => data.items.length === 0}
      >
        {(data) => (
          <div className="divide-y divide-border">
            {data.items.map((shift) => (
              <article className="p-4" key={shift.id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <strong>{shift.staff_name}</strong>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {shift.staff_email} · {shift.role.toUpperCase()}
                    </p>
                  </div>
                  <StatusBadge value={shift.status} />
                </div>
                <p className="mt-3 text-sm">
                  {formatDateTime(shift.clocked_in_at, data.gym_timezone)} →{" "}
                  {shift.clocked_out_at
                    ? formatDateTime(shift.clocked_out_at, data.gym_timezone)
                    : "Open"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Duration {durationLabel(shift.duration_minutes)}
                </p>
              </article>
            ))}
          </div>
        )}
      </QueryState>
      {query.data ? (
        <Pagination
          page={page}
          pages={query.data.page.pages}
          total={query.data.page.total}
          onPage={onPage}
        />
      ) : null}
    </Panel>
  );
}
