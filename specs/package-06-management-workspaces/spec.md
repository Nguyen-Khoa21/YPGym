# Package 6: staff and management workspaces

**Status:** `IMPLEMENTED_VERIFIED` with the gaps listed below (backend commit `05363bb`, web commit `778b8cb`, 2026-11-09). Depends on Packages 1, 2, 3 and 4. Decisions D-01, D-03 and D-07 are approved in [decisions.md](../decisions.md). The backend change is not purely web: it adds `GET /gyms/me`, the shift guard and a scoped analytics summary.

**Verification record.** Backend suite 217 passed and `alembic check` clean (no migration). Web lint 0 errors, type-check and build clean, 36 web tests pass. A Playwright run against a seeded stack passed three times in a row: staff locked, clock in, unlocked, clock out, locked with no further attendance requests; manager sees their gym with no selector and no revenue; owner switches branch and sees one card per gym.

**Known gaps, stated plainly.**

- FR-OPS-009 is only partly met. The gym scope bar is shown on the Attendance and Branches pages. Other operations pages (members, billing, classes, approvals and so on) do not show it yet.
- AC-OPS-011 is verified for the switch, but the test does not assert the interim loading state or that District 1 rows vanish at once.
- AC-OPS-014 is verified at the query-key rule level (a District 11 event leaves District 1 queries stale-free). It was not tested with two live browser sessions.
- AC-OPS-015 and FR-OPS-018 are implemented but not exercised in a browser: the Branches page edit and reassign flows, and double clicks on clock-in, clock-out and manual close (the buttons are disabled while a request is pending).
- The admin class list, peak hours and crowdedness now require a gym for the owner. The admin traffic summary still defaults to District 1 for the owner, because it was outside D-03.
- The member realtime socket and the mobile apps are unchanged.

## Purpose

Business goals served: managers get operational visibility for their own branch (G4), owners get multi-branch insight (G5), and QR attendance stays secure and reliable (G6) because staff act only on their branch and only while on shift.

## Role model (target)

| Role | Gym scope | Attendance operations | Analytics | Sensitive areas |
|---|---|---|---|---|
| Owner (the `admin` role) | All gyms, or one chosen gym | Any gym, no shift needed | Per gym and branch comparison | Billing, revenue, exports, revocation, gym and workforce management, audit |
| Manager | One assigned gym, no selector | Assigned gym, no shift needed | Assigned gym only | None of the owner-only areas |
| Staff | One assigned gym | Assigned gym, only while clocked in | None | None |
| PT | One assigned gym | None | None | None |
| Member | Home gym | Own attendance only | Own gym's member summary | None |

Backend authorization enforces every row. Navigation only reflects it.

## What exists today (evidence)

- `GET /attendance/admin` and `POST /attendance/admin/{id}/manual-close` allow `staff`, `manager` and `admin`. **Nothing checks for an open shift** (no shift reference in `attendance.py` or `attendance_service.py`). Gym scope is enforced through `GymScopeService`, and manual close checks access to the session's gym. A manual close on a session that is not active returns the session unchanged.
- `ManualCloseRequest.reason` is 10 to 1000 characters and the close writes an audit record.
- `StaffService.clock_in` creates a shift at the user's effective gym and rejects a second open shift. `GET /staff/shifts/me` returns `open_shift` (with `gym_id`, no gym name), `recent_shifts` and `gym_timezone`.
- `AdminAttendancePage.tsx` has no gym awareness. The API accepts `gym_id`, and for an admin without one it returns all gyms.
- The realtime socket accepts a first-frame `gym_id`. An admin with none gets all gyms. The web client never sends one, and its refresh invalidates every `dashboard`, `attendance` and `training` query regardless of gym.
- The user payload (`UserPublic`) has no gym field, and no endpoint tells a manager or staff member which gym they are assigned to unless a shift is open.
- `GET /admin/analytics/summary` has no `gym_id`. `AnalyticsService.summary` aggregates membership trends, class popularity, attendance and **revenue across all gyms**, and the endpoint allows managers. `AdminAttendancePage.tsx` calls it.
- `GET /admin/analytics/traffic-summary?gym_id=` and `GET /gyms/{id}/crowdedness` exist and are gym-scoped.
- Backend gym and workforce management exists (`/admin/gym-locations`, `/workforce/assignments`). No web page for it was found.
- Navigation already limits Billing and Classes to admins (`navigation.ts`).

## Functional requirements

**Shift gate (backend)**

| ID | Requirement |
|---|---|
| FR-OPS-001 | A reusable server-side guard allows a `staff` user to use attendance operations only while they have an open shift whose `gym_id` equals their current assigned gym. |
| FR-OPS-002 | The guard applies to `GET /attendance/admin` and `POST /attendance/admin/{id}/manual-close`. Without an open shift it returns 403 with a structured error code `SHIFT_REQUIRED` (assumption, see D-09). |
| FR-OPS-003 | Manager and admin access to those endpoints never depends on a shift. |

**Staff workspace (web)**

| ID | Requirement |
|---|---|
| FR-OPS-004 | When the staff member has no open shift, the attendance workspace shows their gym name, a clocked-out status and a clock-in action. It makes no attendance or occupancy request. |
| FR-OPS-005 | When a shift is open, the workspace shows the gym name, the shift start time, the gym's live occupancy, active and recent sessions of that gym, member search, status and date filters, and pagination. |
| FR-OPS-006 | Clocking out re-locks the workspace immediately. A request that returns `SHIFT_REQUIRED` also switches the page to the locked state instead of showing a generic error. |
| FR-OPS-007 | Manual close asks for a reason of at least 10 characters, closes only an active session of the staff member's gym, and shows the audit-backed result. Closing a session that another operator already closed shows a neutral "already closed" message and refreshes the list. |
| FR-OPS-008 | Staff and PT see no manager analytics, billing, CRM, settings or other gym's data in navigation or by direct URL, and the backend returns 403 for those APIs. |

**Gym scope in the shell**

| ID | Requirement |
|---|---|
| FR-OPS-009 | Every operations page shows the effective gym scope in its header: the gym name for manager and staff, the selected gym or "All branches" for the owner. |
| FR-OPS-010 | The client can learn its own assigned gym without an open shift, through an additive endpoint (decision D-01). |
| FR-OPS-011 | A manager sees no branch selector and cannot request another gym. A request naming another gym returns 403 (already enforced for attendance by `GymScopeService`). |

**Owner workspace**

| ID | Requirement |
|---|---|
| FR-OPS-012 | The owner has a branch selector on attendance and analytics pages. Every gym-specific query key includes the gym id, and changing the selector never shows the previous branch's data. |
| FR-OPS-013 | The owner overview shows one card per active gym: live occupancy, last-month busiest and quietest windows, visits, unique members. Percentages of different gyms are never added into one figure. A card links into that branch. |
| FR-OPS-014 | `GET /admin/analytics/summary` accepts `gym_id`. A manager is always scoped to their gym. Revenue totals are returned only to the owner (decision D-07). The attendance page passes the selected gym. |
| FR-OPS-015 | The owner can list, create and edit gym locations and list and change workforce assignments from the web, using the existing admin endpoints. |

**Realtime and cache**

| ID | Requirement |
|---|---|
| FR-OPS-016 | The realtime client sends the gym the page is scoped to (the selected gym for the owner, none for staff and manager whose scope is fixed). Switching branch reconnects or resubscribes. |
| FR-OPS-017 | A realtime event refreshes only the active queries of the affected gym. An event for another gym does not refetch the current branch's data. |
| FR-OPS-019 | Where the owner compares or manages branches, an omitted gym is rejected with 422 `GYM_SCOPE_REQUIRED` instead of silently using District 1: the admin class list, `GET /analytics/peak-hours` and `GET /attendance/crowdedness` (decision D-03). The web pages always send a gym. |
| FR-OPS-018 | Double clicks on clock-in, clock-out and manual close do not create duplicate actions or show raw errors. |

## Non-functional requirements

- **NFR-OPS-001.** No cross-gym data leaves the API for a manager or staff token, whatever parameters are sent. Tests assert 403 or an empty result, never another gym's rows.
- **NFR-OPS-002.** The shift guard is one dependency or service method reused by every gated endpoint, not copied per endpoint.
- **NFR-OPS-003.** All changes are additive for the mobile and scanner clients. Existing response fields keep their names and types.

## Acceptance criteria

**AC-OPS-001** Given a District 1 staff member with no open shift, when they call `GET /attendance/admin`, then the response is 403 with code `SHIFT_REQUIRED`.

**AC-OPS-002** Given the same staff member after clocking in, when they call `GET /attendance/admin`, then they receive only District 1 sessions, and a request with `gym_id` of District 11 returns 403.

**AC-OPS-003** Given a staff member whose open shift is at District 1 but whose assignment was changed to District 11, when they call the endpoint, then the response is 403 `SHIFT_REQUIRED`.

**AC-OPS-004** Given a manager and an owner with no shift, when they call the same endpoints, then they succeed within their scope.

**AC-OPS-005** Given a staff member who clocks out, when the workspace is open, then it switches to the locked state without a page reload and no further attendance requests are made.

**AC-OPS-006** Given an active session at District 1, when a District 1 staff member on shift closes it with a 10-character reason, then the session is `manual_closed`, an audit record exists, and District 11 occupancy is unchanged.

**AC-OPS-007** Given a District 11 session, when a District 1 staff member or manager calls manual close for it, then the response is 403 and the session is unchanged.

**AC-OPS-008** Given a session already closed by someone else, when manual close is requested, then no error is shown and the list refreshes to the closed state.

**AC-OPS-009** Given a staff or PT token, when any `/admin/analytics/*` endpoint is called, then the response is 403.

**AC-OPS-010** Given a manager at District 1, when `GET /admin/analytics/summary` is called with no gym, then every figure covers District 1 only and no revenue field carries data; with `gym_id` of District 11, the response is 403.

**AC-OPS-011** Given the owner on the attendance page, when the selector changes from District 1 to District 11, then the District 1 rows disappear immediately, a loading state shows, and only District 11 rows appear.

**AC-OPS-012** Given the owner overview, when it loads, then it shows one card for each active gym with its own figures, and no card contains a combined percentage.

**AC-OPS-013** Given a manager's session, when the attendance page loads, then no branch selector is rendered and the header shows the assigned gym name.

**AC-OPS-014** Given a realtime occupancy event for District 11, when a District 1 manager's page is open, then no District 1 query is refetched because of it.

**AC-OPS-016** Given an owner token, when the admin class list, `/analytics/peak-hours` or `/attendance/crowdedness` is called with no gym, then the response is 422 `GYM_SCOPE_REQUIRED`; with a gym it returns that gym's data.

**AC-OPS-015** Given the owner on the gym management page, when a gym is edited or a staff member is reassigned, then the change is saved through the existing endpoints and an audit-visible result is shown.

## Tasks

**Backend**

- **T6-01** Add the shift guard as one reusable dependency or service method that compares the open shift's gym with the staff member's current assignment. Closes FR-OPS-001, FR-OPS-003, NFR-OPS-002.
- **T6-02** Apply the guard to `GET /attendance/admin` and `POST /attendance/admin/{id}/manual-close` with error code `SHIFT_REQUIRED`. Closes FR-OPS-002, AC-OPS-001 to 004.
- **T6-03** Add the additive "my gym" endpoint chosen in D-01. Closes FR-OPS-010.
- **T6-04** Scope `AnalyticsService.summary` by `gym_id`, force manager scope, and restrict revenue per D-07. Closes FR-OPS-014, NFR-OPS-001, AC-OPS-010.
- **T6-05** Backend tests in `test_staff_operations.py` and `test_attendance_gym_isolation.py` style: AC-OPS-001 to 004, 006 to 010. Run against the isolated stack.

**Frontend**

- **T6-06** Shell: show effective gym scope in the operations and staff headers using the T6-03 endpoint, and add the owner branch selector component. Closes FR-OPS-009, 011, 012, AC-OPS-013.
- **T6-07** Staff attendance workspace: locked and unlocked states, clock-in action, `SHIFT_REQUIRED` handling. Closes FR-OPS-004 to 006, AC-OPS-005.
- **T6-08** `AdminAttendancePage`: gym-aware query keys, selector wiring for the owner, search and filter controls, manual-close flow with neutral already-closed handling. Closes FR-OPS-005, 007, 012, 018, AC-OPS-008, AC-OPS-011.
- **T6-09** Realtime: send the scoped gym in the first frame, resubscribe on branch change, and invalidate only matching-gym query keys. Closes FR-OPS-016, 017, AC-OPS-014. Changes `attendanceRealtime.ts` and `AttendanceRealtime.tsx`, and their tests.
- **T6-10** Owner overview with one card per gym, using `/gyms`, `/gyms/{id}/crowdedness` and the admin traffic summary. Closes FR-OPS-013, AC-OPS-012.
- **T6-11** Gym location and workforce assignment management page and route. Closes FR-OPS-015, AC-OPS-015.
- **T6-12** Navigation and route guards: confirm staff, PT and manager entries match the role table. Update `navigation-config.test.mjs`. Closes FR-OPS-008.

- **T6-14** Replace the District 1 fallbacks with `GYM_SCOPE_REQUIRED` for admin on the three endpoints and update the web callers and tests. Closes FR-OPS-019, AC-OPS-016.

**Checks**

- **T6-13** Full backend suite, `npm run lint`, `npm run build`, `npm test`, `alembic check` (no migration expected). Manual walk-through of AC-OPS-005, 011, 013 with seeded users `staffdist1`, `managerdist1`, `owner`.

## Out of scope

Native mobile, the scanner app, new roles, multi-gym managers, and recommendations.

## Dependencies

Packages 1 to 4. Decisions D-01, D-03 and D-07 before T6-03, T6-04 and T6-06.
