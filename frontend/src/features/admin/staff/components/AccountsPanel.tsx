import type { UseQueryResult } from "@tanstack/react-query";

import { QueryState } from "@/components/common/QueryState";
import { Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import type { StaffAccountPage } from "@/types/operations";

type Props = {
  query: UseQueryResult<StaffAccountPage>;
  page: number;
  onPage: (page: number) => void;
};

export function AccountsPanel({ query, page, onPage }: Props) {
  return (
    <Panel
      title="Workforce accounts"
      detail={
        query.data
          ? `Internal sign-ins use @${query.data.internal_email_domain}. This is not a claimed mailbox domain.`
          : "Distinct staff and PT credentials."
      }
    >
      <QueryState
        query={query}
        className="m-4"
        loading={{ title: "Loading accounts" }}
        retry
        empty={{
          title: "No workforce accounts",
          message: "Create the first individual staff or PT account.",
        }}
        isEmpty={(data) => data.items.length === 0}
      >
        {(data) => (
          <div className="divide-y divide-border">
            {data.items.map((account) => (
              <article
                className="flex flex-wrap items-start justify-between gap-4 p-4"
                key={account.id}
              >
                <div>
                  <strong>{account.name}</strong>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {account.email}
                    {account.phone ? ` · ${account.phone}` : ""}
                  </p>
                  <p className="mt-2 text-xs font-semibold">
                    {account.gym_name ? `Gym: ${account.gym_name}` : "No gym assigned"}
                  </p>
                  <p className="mt-1 text-xs">
                    {account.trainer_profile_id
                      ? "Linked PT profile"
                      : account.role === "staff"
                        ? "Staff operations access"
                        : "PT profile pending"}
                  </p>
                </div>
                <div className="grid justify-items-end gap-2">
                  <StatusBadge value={account.role} />
                  <StatusBadge
                    value={account.must_change_password ? "password change required" : "active"}
                  />
                </div>
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
