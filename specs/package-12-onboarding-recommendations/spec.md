Part of the [post-multigym master prompt](../post-multigym-master-prompt.md). Read its sections 0 to 3 first (operating rules, evidence, defaults, cross-cutting rules).

# Package 12: New-member questions, recommendations, owner insights

**Goal.** Ask a short radio-button questionnaire, use the answers to recommend a gym and quiet hours, and give the owner aggregate data to plan from. **Never recommend from an unanswered question.**

### Questions (all radio buttons, one screen, about one minute)

Required to count as "complete" (the three the owner asked for):
1. Are you new to the gym? Yes / No.
2. Would you like to work out in uncrowded hours? Yes / No.
3. Which location are you closer to? One radio per **active gym from `GET /gyms`** (today District 1 and District 11). Never hard-code gym names.

Suggested extras, optional (they make the owner's data more useful):
4. Main goal: Lose weight / Build muscle / Stay fit and healthy / Improve stamina / Not sure yet.
5. When can you usually train? Early morning (05:00 to 08:00) / Daytime (08:00 to 16:00) / Evening (16:00 to 20:00) / Night (20:00 to 24:00).
6. How many days a week? 1 to 2 / 3 to 4 / 5 or more.
7. Interested in group classes? Yes / No.
8. Interested in a personal trainer? Yes / No.

Show one line of purpose text ("We use this to suggest quiet hours and your closest gym"). Do **not** ask for health or medical data.

### Requirements

| ID | Requirement |
|---|---|
| FR-ONB-001 | New table `member_onboarding_profiles` (migration `0023`): `id`, `user_id` unique FK to `users` (cascade), nullable answer columns for Q1 to Q8 (booleans for Q1, Q2, Q7, Q8; `closer_gym_id` FK to `gym_locations`; short string columns with `CHECK` constraints for Q4 to Q6), `completed_at`, `dismissed_at`, timestamps. "Complete" means Q1 to Q3 are non-null. |
| FR-ONB-002 | Endpoints (member role only, user id from the JWT, placed under the existing user/me router, follow its conventions): `GET .../onboarding` (answers plus `status`: `not_started`, `skipped`, `partial`, `complete`), `PUT .../onboarding` (validated upsert; partial saves allowed), `POST .../onboarding/skip`. The closer gym must be an active gym. |
| FR-ONB-003 | Web: **immediately after a member's first successful login** (no row yet), open `/app/onboarding` as the first screen, once. It has a visible "Skip for now". A skip stores `dismissed_at` and the member is not asked again. Profile gets a "Training preferences" section to answer or edit later. Reuse React Hook Form, Zod and shared form components; build radios as accessible `fieldset`/`legend` groups. |
| FR-ONB-004 | Mobile: the same questionnaire as one screen in the member app, reached once after first login and from Profile. Reuse the `ui` components and `lib/gyms.ts`. |
| FR-ONB-005 | `GET .../recommendations` (member only). Pure, explainable rules, no machine learning: **R1 location**: only if Q3 is answered and that gym is active, return `recommended_gym`. **R2 quiet hours**: only if Q2 is "Yes", return the quietest two-hour window from the previous-month traffic data of the recommended gym (or of the home gym if Q3 is unanswered and the member has a membership). If Q5 is answered, choose the quietest window that overlaps the member's training window. If `data_sufficient` is false, return `quiet_hours: null` with `reason: "not_enough_data"`; never invent numbers. Each rule is independent; an unanswered input yields **no** recommendation for that rule. Reuse `TrafficAnalyticsService`/repository functions; do not call the manager-only endpoint and do not expose another member's data. |
| FR-ONB-006 | Where recommendations show: (a) the membership purchase and renewal gym picker marks the recommended gym "Recommended for you" and preselects it only when the member has no home gym; (b) the member class list marks that gym's tab "Recommended for you". Default class gym order stays: home gym, then recommended gym, then the first active gym. The member can always choose any gym. (c) The member dashboard shows a small card "Quiet time for you: {window} at {gym}" only when R2 produced a result. Web and mobile. |
| FR-ONB-007 | Owner and manager insights: `GET /admin/analytics/onboarding-insights?gym_id=` returns counts and percentages for respondents, response rate (respondents divided by members), new-to-gym, prefers uncrowded hours, closer-gym split next to the actual home-gym split, goal, training window, frequency, class interest, PT interest. Owner (`admin`) may pass any gym or none; manager is locked to the assigned gym (scoped by `closer_gym_id`; naming another gym is `403`); staff and PT get `403`. Hide any group below 5 responses (config value, default 5). Show it as a panel on the admin overview for manager/admin using existing `Panel` and `MetricCard`. Percentages of different gyms are never summed (same rule as occupancy). |
| FR-ONB-008 | Privacy: answers are deleted with the account (cascade); they are not written to logs, audit metadata or CSV exports; `docs/policies/security.md` states what is stored and why. |

### Acceptance criteria

- **AC-ONB-001.** A member who answered Q3 = District 11 sees District 11 marked "Recommended for you" in checkout and in the class list; a member who skipped sees no such marker anywhere.
- **AC-ONB-002.** Q2 = "No" or unanswered: no quiet-hours card and `quiet_hours` absent from the response.
- **AC-ONB-003.** Q2 = "Yes", enough data: the card shows the quietest window inside the member's Q5 window. Not enough data: the card says "Not enough attendance data yet" and shows no percentage.
- **AC-ONB-004.** A staff token gets `403` on the insights endpoint; a District 1 manager naming District 11 gets `403`; the owner can read both.
- **AC-ONB-005.** A group of 4 responses is returned as hidden/suppressed, never as numbers.
- **AC-ONB-006.** A member cannot read or write another member's answers (no user id in any path or body).
- **AC-ONB-007.** An inactive or unknown gym id in Q3 is rejected.

### Tasks

T12-01 spec, decisions D-13 and D-14. T12-02 migration `0023`, model, repository. T12-03 schemas and service (rules R1, R2). T12-04 endpoints. T12-05 web questionnaire, Profile section, recommendation markers, dashboard card. T12-06 mobile screen and markers. T12-07 insights endpoint and admin panel. T12-08 tests (answered versus unanswered matrix, scope matrix, suppression). T12-09 docs.

**Out of scope:** machine learning, push notifications, health questions, changing membership pricing from answers.

