# Completed packages 1 to 4

This is a short evidence summary, not a re-specification. It records what the repository actually delivers, the commit that delivered it, and the tests that cover it. Branch: `codex/feat/web-multigym-foundation`.

**Verification run (2026-11-09).** The full isolated backend suite, run on the Package 4 content in a standalone PostgreSQL 16 and Redis stack, passed 209 tests. `alembic upgrade head`, one downgrade and upgrade cycle, and `alembic check` were clean at revision `20261109_0021`. Web lint had 0 errors, TypeScript and the production build passed, and 26 web tests passed. For Packages 1 to 3 this is suite-level evidence: the named tests exist and pass, but their individual assertions were not re-audited for this document.

## Package 1: multi-location foundation

- **Commit:** `f46aa78`. **Migration:** `20261107_0020`.
- **Delivers:** `gym_locations`, `workforce_gym_assignments` (one active assignment per user), gym columns on devices, attendance, memberships, classes, shifts and broadcasts, a District 1 backfill, `GET /gyms`, `GET /gyms/{id}`, and `GymScopeService` for role-scoped gym resolution.
- **Tests:** `test_gym_locations.py` (role-safe management, cross-location denial, required columns and District 1 defaults), `test_demo_seed.py`.
- **Status:** `IMPLEMENTED_VERIFIED` at suite level.

## Package 2: gym-scoped attendance and realtime

- **Commit:** `3071514`.
- **Delivers:** scanner device bound to a gym, per-gym occupancy and cache, gym-scoped attendance history and manual close, a realtime WebSocket whose first frame may name a gym.
- **Tests:** `test_attendance_gym_isolation.py` (scanner, membership, occupancy and cache isolation; manager history and manual close limited to the assigned gym; timeout reconciliation per gym), `test_attendance_realtime.py`.
- **Status:** `IMPLEMENTED_VERIFIED` at suite level.

## Package 3: historical peak and off-peak analytics

- **Commit:** `f7f7dd8`.
- **Delivers:** `GET /attendance/traffic-summary` (member, home gym only) and `GET /admin/analytics/traffic-summary?gym_id=` (manager locked to the assigned gym). Previous completed month in the gym timezone, 15-minute overlap sampling, two-hour windows, busiest and quietest windows, a weekday heatmap, and an honest insufficient-data state. See `docs/api/traffic-analytics.md`.
- **Tests:** `test_traffic_analytics.py`, `test_traffic_analytics_storage.py`.
- **Status:** `IMPLEMENTED_VERIFIED` at suite level. No web page consumes the member endpoint yet, and no source file imports Recharts yet (Package 5).

## Package 4: memberships, payments, classes and broadcasts

- **Commit:** `e161f32`. **Migration:** `20261109_0021`. API notes: `docs/api/gym-scoped-services.md`.
- **Delivers:** gym choice on first purchase and renewal, `payments.gym_id`, the membership gym applied only after verified payment, gym-scoped classes and room overlap, admin-only class administration, chain-wide or per-gym broadcasts, and gym names on invoices and notifications.
- **Status:** `IMPLEMENTED_VERIFIED` for checkout, renewal, class scoping and broadcast scoping. Two behaviors are `IMPLEMENTED_UNTESTED`: the payOS webhook moving a payment to `paid_review` when the gym turned inactive after checkout, and `409 IDEMPOTENCY_KEY_REUSED` when a key is replayed with a different plan or gym.

## Gaps found in completed work

Some of these are defects in earlier scope (G-08 is a security gap), and some are work that later packages own. Each row names where it is handled.

| ID | Finding | Where | Handled in |
|---|---|---|---|
| G-01 | Staff can use attendance operations without an open shift. Nothing in the attendance endpoints or service checks a shift. | `attendance.py`, `attendance_service.py` | Package 6 |
| G-02 | The admin attendance page has no gym selector or gym label, although the API accepts `gym_id`. | `AdminAttendancePage.tsx` | Package 6 |
| G-03 | The realtime socket defaults to all gyms for an admin, and the web client never sends `gym_id`. Refresh invalidates all attendance, dashboard and training queries regardless of gym. | `attendance_realtime.py`, `attendanceRealtime.ts` | Package 6 |
| G-04 | The admin class list, `GET /analytics/peak-hours` and `GET /attendance/crowdedness` fall back to District 1 for an admin who sends no gym. | `classes.py`, `attendance.py` | Decision D-03 |
| G-05 | No test covers the inactive-gym webhook path or the idempotency conflict. | Package 4 tests | Decision D-05 |
| G-06 | The dashboard still returns a QR quick action, and the dashboard page renders it. | `dashboard_service.py`, `MemberDashboardPage.tsx` | Package 5 |
| G-07 | `docs/policies/roles.md`, the route-screen map and the architecture docs do not yet describe the gym-scoped roles. | `docs/` | Package 8 |
| G-08 | `GET /admin/analytics/summary` has no gym parameter and aggregates membership, class, attendance and revenue for all gyms. It allows managers, so a manager can read chain-wide totals. | `attendance.py` (`analytics_summary`), `analytics_service.py` | Package 6 (T6-04) |
