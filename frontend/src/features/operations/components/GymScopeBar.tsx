import { MapPin } from "lucide-react";

import type { OperationsScope } from "../useOperationsScope";

/** Shows which gym the page covers. The owner can change it; managers and staff cannot. */
export function GymScopeBar({
  scope,
  allowAll = true,
}: {
  scope: OperationsScope;
  allowAll?: boolean;
}) {
  return (
    <div
      className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 text-sm"
      data-testid="gym-scope"
    >
      <MapPin className="size-4 text-primary" aria-hidden />
      {scope.isOwner ? (
        <label className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">Branch</span>
          <select
            className="h-9 rounded-md border border-input bg-card px-2"
            value={scope.gymId}
            onChange={(event) => scope.selectGym(event.target.value)}
            disabled={!scope.ready}
          >
            {allowAll ? <option value="">All branches</option> : null}
            {scope.gyms.map((gym) => (
              <option value={gym.id} key={gym.id}>
                {gym.name} · {gym.district}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <span>
          <span className="font-semibold">Your gym:</span> {scope.gymName ?? "Loading"}
        </span>
      )}
    </div>
  );
}
