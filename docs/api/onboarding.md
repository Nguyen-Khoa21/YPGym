# New-member questionnaire, recommendations and insights (Package 12)

Spec: `specs/package-12-onboarding-recommendations/spec.md`.

| Endpoint | Role | Purpose |
|---|---|---|
| `GET /api/v1/users/me/onboarding` | member | Own answers and `status`: `not_started`, `skipped`, `partial`, `complete`. |
| `PUT /api/v1/users/me/onboarding` | member | Replaces own answers. Partial saves are allowed; omitted answers become null. `closer_gym_id` must be an active gym (`422` otherwise). Unknown fields are rejected. |
| `POST /api/v1/users/me/onboarding/skip` | member | Stores `dismissed_at` so the prompt is not repeated. Does not change a completed profile. |
| `GET /api/v1/users/me/recommendations` | member | `recommended_gym` and `quiet_hours`. Empty object when nothing was answered. |
| `GET /api/v1/admin/analytics/onboarding-insights?gym_id=` | manager, admin | Aggregate counts. Manager is locked to the assigned gym (`403` for another). Staff and PT get `403`. |

"Complete" means the three required questions are answered: new to the gym, uncrowded hours, closer gym.

## Recommendation rules

- **R1 location:** only when the closer gym is answered and still active.
- **R2 quiet hours:** only when "uncrowded hours" is Yes. Uses the previous completed month's two-hour traffic buckets of the recommended gym (or the member's home gym when no closer gym was answered). When the usual training time is answered, only windows that overlap it are considered. Without enough data the response carries `quiet_hours_reason: "not_enough_data"` and no window or percentage.
- An unanswered input produces no recommendation for that rule. Fields that are null are omitted from the response.

## Insights

Counts cover members who completed the three required questions. Any metric with fewer than `ONBOARDING_INSIGHT_MIN_GROUP_SIZE` (default 5) answers, and any answer group below it, is returned with `suppressed: true` and no numbers. The owner view without a gym also returns closer-gym versus current-home-gym counts. Percentages of different gyms are not summed. The response rate is only given for the all-branches view.
