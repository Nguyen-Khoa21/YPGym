import { useQuery } from "@tanstack/react-query";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MetricCard, Panel } from "@/components/operations/OperationsUi";
import { useAuth } from "@/features/auth/AuthContext";
import { GymScopeBar } from "@/features/operations/components/GymScopeBar";
import { useOperationsScope } from "@/features/operations/useOperationsScope";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";

type Bucket = {
  key: string;
  label: string;
  count: number | null;
  percent: number | null;
  suppressed: boolean;
};
type Metric = {
  key: string;
  label: string;
  answered: number | null;
  suppressed: boolean;
  buckets: Bucket[];
};
type SplitRow = {
  gym_id: string;
  gym_name: string;
  closer_count: number | null;
  closer_suppressed: boolean;
  home_members: number | null;
  home_suppressed: boolean;
};
type Insights = {
  gym_id: string | null;
  min_group_size: number;
  members: number;
  respondents: number | null;
  respondents_suppressed: boolean;
  response_rate_percent: number | null;
  metrics: Metric[];
  gym_split: SplitRow[];
};

/** Aggregate answers from the new-member questions. Groups smaller than the configured minimum are never shown as numbers. */
export function OnboardingInsightsPanel() {
  const { token } = useAuth();
  const scope = useOperationsScope();
  const insights = useQuery({
    queryKey: ["onboarding-insights", scope.gymParam],
    enabled: Boolean(token) && scope.ready,
    queryFn: ({ signal }) =>
      apiRequest<Insights>(
        `/admin/analytics/onboarding-insights${scope.gymParam ? `?gym_id=${scope.gymParam}` : ""}`,
        { token, signal },
      ),
  });
  const data = insights.data;
  return (
    <Panel
      className="mt-8"
      title="New-member answers"
      detail="What members told us when they joined. Percentages of different gyms are never added together."
    >
      <GymScopeBar scope={scope} />
      {insights.isLoading ? <LoadingState title="Loading member answers" /> : null}
      {insights.isError ? (
        <ErrorState
          title={toUiError(insights.error).title}
          message={toUiError(insights.error).message}
        />
      ) : null}
      {data ? (
        <div className="grid gap-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <MetricCard
              label={scope.gymParam || !scope.isOwner ? "Members at this gym" : "Members"}
              value={data.members}
            />
            <MetricCard
              label="Answered the questions"
              value={
                data.respondents_suppressed
                  ? `Fewer than ${data.min_group_size}`
                  : (data.respondents ?? 0)
              }
              tone="lime"
            />
            <MetricCard
              label="Response rate"
              value={data.response_rate_percent === null ? "n/a" : `${data.response_rate_percent}%`}
              detail={
                data.response_rate_percent === null
                  ? "Shown for all branches once enough members answered"
                  : undefined
              }
            />
          </div>
          {data.respondents_suppressed ? (
            <p className="rounded-xl bg-muted p-4 text-sm">
              Fewer than {data.min_group_size} members have answered, so results stay hidden to
              protect privacy.
            </p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {data.metrics.map((metric) => (
                <article className="rounded-2xl border border-border p-4" key={metric.key}>
                  <h3 className="text-sm font-extrabold">{metric.label}</h3>
                  {metric.suppressed ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      Hidden: fewer than {data.min_group_size} answers.
                    </p>
                  ) : (
                    <ul className="mt-3 grid gap-2">
                      {metric.buckets.map((bucket) => (
                        <li
                          className="flex items-center justify-between gap-3 text-sm"
                          key={bucket.key}
                        >
                          <span>{bucket.label}</span>
                          {bucket.suppressed ? (
                            <span className="text-xs text-muted-foreground">
                              Fewer than {data.min_group_size}
                            </span>
                          ) : (
                            <strong>
                              {bucket.count} · {bucket.percent}%
                            </strong>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              ))}
            </div>
          )}
          {data.gym_split.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <caption className="mb-2 text-left text-sm font-extrabold">
                  Closest gym versus actual home gym
                </caption>
                <thead>
                  <tr className="text-xs uppercase text-muted-foreground">
                    <th className="py-2 pr-4">Gym</th>
                    <th className="py-2 pr-4">Said closest</th>
                    <th className="py-2">Current members</th>
                  </tr>
                </thead>
                <tbody>
                  {data.gym_split.map((row) => (
                    <tr className="border-t border-border" key={row.gym_id}>
                      <td className="py-2 pr-4 font-semibold">{row.gym_name}</td>
                      <td className="py-2 pr-4">
                        {row.closer_suppressed
                          ? `Fewer than ${data.min_group_size}`
                          : row.closer_count}
                      </td>
                      <td className="py-2">
                        {row.home_suppressed
                          ? `Fewer than ${data.min_group_size}`
                          : row.home_members}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : null}
    </Panel>
  );
}
