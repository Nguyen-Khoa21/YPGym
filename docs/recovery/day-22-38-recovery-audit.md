# Day 21-38 Crash-Recovery Audit

Last updated: 2026-07-18 (recovery implementation and verification complete)

## Recovery safety checkpoint

- External backup: `C:\Users\Admin\ypgym-recovery-20260718-141935`
- Validation: 211 eligible project files copied and SHA-256 checked; 0 missing copies and 0 hash mismatches.
- Initial branch/commit: `main` at `a91573b` (`UI redesign`), tracking `origin/main`.
- Initial working tree: 23 modified tracked files, 0 staged files, 36 untracked files, and 0 deleted files.
- Conflict/truncation check: no merge markers and no zero-byte project files found.
- Initial diagnostic issues: `git diff --check` reported two trailing-space lines in the revised plan; Docker Desktop was not running, so `docker compose ps` could not connect to the Docker API.

## Initial Day 21-38 matrix

The statuses below describe the interrupted state before recovery edits. Static code presence is not treated as proof of integration or completion.

| Day | Status | Files and database evidence | API, service, permission, and validation evidence | Frontend and verification evidence | Missing integration and recovery action |
|---|---|---|---|---|---|
| 21 | partial | `models/enums.py`, `models/membership.py`, migration `20260716_0004`, `lifecycle_service.py`, and `workers/celery_app.py` contain the required states, freeze fields/requests, cancellation/revocation fields, lifecycle derivation, and scheduled synchronization. | Member request and manager/admin decision endpoints are registered. QR eligibility calls the central lifecycle service. Freeze dates/reasons and cancellation/revocation reasons are validated. | `MembershipRequestsPage.tsx` exists but is not registered; policy/profile copy still says lifecycle work is planned. No tests exist. | Prove migration state and lifecycle transitions; connect member/admin routes; reconcile outdated copy; add focused tests before relying on later attendance/class access. |
| 22 | partial | `operations_repository.py`, `operations_service.py`, `admin.py`, and schemas implement paginated CRM queries, search, role/tier/status/expiry filters, deterministic sorting, summaries, and a composite detail response. | `/admin/members` and `/admin/members/{id}` are admin-only and layered. Response omits password/token fields. | `AdminMembersPage.tsx` and `AdminMemberDetailPage.tsx` exist with TanStack Table and states, but `router.tsx` still serves planned placeholders. No API/browser verification. | Register the real pages, add expiry controls and permission-correct routing, test filters/detail query shapes, and verify responsive states. |
| 23 | partial | Migration `20260716_0004` adds one-open-request partial unique indexes, explicit outcomes, actor/reviewer/timestamps, revocation data, and audit logs. | Transactional request/decision/revocation services and endpoints exist with mandatory reasons and manager/admin or admin guards. | Request and decision UI exists but is unreachable from the router. No duplicate/decision/revocation tests. | Connect UI, verify rollback/idempotency and audit rows, and prove revoked access denial. |
| 24 | partial | `notification_preferences` and `notifications` models/migration plus repository/service code exist. | Preferences, paginated notification list, mark-one, and mark-all endpoints are registered and member-only. | Preference/inbox pages exist but are not routed or linked; no persistence/read-state tests. | Register and link pages, add pagination/state polish as needed, and verify channel/read behavior. |
| 25 | partial | Broadcast model/migration and reminder dedupe records exist; Celery Beat schedules 7/3/1-day reminder work. | Manager/admin broadcast CRUD/list and member active-broadcast endpoint exist; service respects preferences and active periods. | `AdminBroadcastsPage.tsx` exists but is not routed; member dashboard does not fetch broadcasts. No worker/dedupe evidence. | Connect broadcast administration and dashboard cards, then prove active-period filtering and reminder deduplication. |
| 26 | partial | Filtered billing repositories/services and CRM/billing CSV generation with formula-injection escaping and export audit writes exist. | New `/admin/billing/*` routes are admin-only; legacy `/billing/admin/payments` remains. | Upgraded billing page is routed, but the protected route still admits staff/manager before the API returns 403; visible filters cover only member/status. No CSV comparison test. | Correct route roles, expose required filters consistently, and verify CSV rows exactly match active filters. |
| 27 | partial | Audit model/indexes, filtered repository/service, and audit schema exist. | `/admin/audit-logs` is manager/admin-only with date/action/actor/target/entity filters. | `AdminAuditPage.tsx` exists but is not routed or in navigation. No staff-denial/manager-access tests. | Connect page/navigation and prove the documented role matrix. |
| 28 | partial | Existing `system_configurations` is reused; centralized typed rules and Redis cache/invalidation service exist. | Manager/admin list/update endpoints validate safe bounds and audit before/after values. | `AdminSettingsPage.tsx` exists but is not routed. No cache invalidation verification. | Connect page/navigation and test database fallback, Redis cache fill, and invalidation. |
| 29 | partial | Migration `20260716_0005` and models create `iot_devices`, `attendance_sessions`, `attendance_events`, active-session uniqueness, and useful indexes. | Attendance repository uses database locking and indexed active-session queries. | ERD and route-screen map still describe attendance as future. Alembic file/application state is not verified. | Compare models/migration/database, apply only after review, and update data/route documentation. |
| 30 | partial | Redis-tracked signed JWT/JTI rotation and configuration-backed TTL are implemented in `attendance_service.py`. | `GET /attendance/qr-token/me` is member-only and calls central membership eligibility; invalid/superseded/expired token codes exist. | No QR page was saved; `router.tsx` still renders a planned state. No token-state tests. | Build and route the real QR page with countdown/refresh/blocked states and verify rotation/supersession/ineligibility. |
| 31 | partial | Hashed IoT credential storage and scanner persistence are present. | Device-authenticated check-in/check-out endpoints and machine-readable scanner codes exist. | `docs/api/iot-scanner.md` is absent. No contract or unauthorized-device verification. | Add the scanner contract document and test every stable error code and concurrency path. |
| 32 | partial | `iot-simulator/app/main.py`, `.env.example`, README, Dockerfile, and optional Compose profile exist. | Simulator calls the real endpoint with device ID and API key. | No execution evidence; scenario coverage appears CLI-driven rather than automated. | Verify container/CLI operation and document repeatable valid/invalid/expired/inactive/unauthorized/duplicate scenarios. |
| 33 | partial | Attendance service/repository implements active-session uniqueness, checkout, timeout events, manual close, and Celery scheduling. | Scanner checkout and staff/manager/admin manual-close endpoints exist; reasons and audits are enforced. | No member/admin attendance UI exists. No timeout retry or occupancy-decrease tests. | Add focused lifecycle tests, connect UI actions, and verify transaction/cache consistency. |
| 34 | partial | PostgreSQL active-session count is the source of truth; Redis caches a 30-second crowdedness snapshot and configuration. | Authenticated crowdedness endpoint returns count, capacity, percentage, status, and timestamp with required thresholds. | No dashboard integration or reconciliation/threshold tests. | Prove Redis miss/stale reconciliation and connect reusable occupancy cards. |
| 35 | partial | Member/admin attendance repositories return paginated sessions and event/device details. | Member-only history and staff/manager/admin operations endpoints exist; manual close is guarded. | No member history or admin attendance page was saved; route remains a placeholder. | Build both responsive UIs with filters/states/manual-close controls and test role behavior. |
| 36 | partial | Attendance event aggregation by PostgreSQL weekday/hour is implemented. | `/admin/analytics/peak-hours` is manager/admin-only and validates range order/maximum. | No Recharts/accessibility-grid UI was saved and no empty/populated range test exists. | Build analytics UI and verify all 168 cells, KPIs, empty ranges, and permissions. |
| 37 | partial | Migration `20260716_0005` and models create trainers, classes, bookings, and waitlists with capacity/time/uniqueness/index constraints. | Minimal trainer lookup/seed support exists; later booking workflow is not implemented. | ERD/route documentation is stale. Migration is unverified. | Validate schema/head, add constraint tests, and update relational/route documentation without expanding into Day 39+. |
| 38 | partial | Class repository/service and audit writes exist. | Admin-only list/create/update/cancel endpoints validate timezone, future time, capacity, trainer availability, overlap, and cancellation reason. | No `AdminClassesPage` was saved; `/admin/classes` remains planned. No CRUD/overlap/permission verification. | Build and route the schedule/table/dialog UI, then test CRUD, overlap, cancellation, and responsive behavior. |

## Resume point

1. Highest day fully complete before this scope: Day 20, based on the prior handoff and commit history; it still requires regression verification in this recovery.
2. Earliest incomplete dependency: Day 21 membership lifecycle. Its backend is substantial but not migration-verified, tested, or connected in the UI.
3. Later work to preserve: the untracked Days 22-38 models, migrations, repositories, services, endpoints, worker tasks, simulator, React pages, types, CSS, and dependency additions.
4. Out-of-scope work to leave bounded: full PT management/assignment, member class booking/waitlist workflows, Expo/mobile, live payment processing, AI/personalization, and physical hardware integration.

## Failure classification at initial checkpoint

- Pre-existing baseline issue: the repository has no substantive automated test suite; `backend/app/tests` contains only `__init__.py`.
- Crash/interruption issues: saved feature pages are not registered, several required frontend pages were not saved, documentation still describes implemented backend APIs as planned, and migration/database state is unknown.
- New recovery issues: none yet; no implementation repair has been attempted at this checkpoint.
- External blocker: Docker Desktop was not running during Stage 0. This is not yet considered a milestone blocker because local static checks and Docker startup recovery remain available.

## Final Day 21-38 matrix

The initial matrix above is intentionally preserved as crash evidence. This matrix describes the recovered working tree after implementation and regression verification.

| Day | Final status | Completion and verification evidence |
|---|---|---|
| 21 | complete | Central effective-state derivation covers pending verification, active, expiring soon, expired, frozen, cancelled, and revoked; freeze/cancellation decisions, revocation, worker synchronization, QR eligibility reuse, policy UI, and boundary tests are connected. Cancellation eligibility now re-derives stale state. |
| 22 | complete | Admin-only paginated CRM and composite member details are routed with search, role/tier/status/expiry filters, deterministic sort, KPIs, states, TanStack Table, pagination, and filtered CSV. Live filtered response/detail/export checks passed. |
| 23 | complete | One-open-request constraints, reasoned decisions, required cancellation outcomes, admin revocation, audit records, member self-service, admin detail actions, and limited manager/admin approval queue are connected. Manager access/staff denial and live decisions passed. |
| 24 | complete | Preference get/update, in-app records, paginated inbox, read-one/read-all, routed settings/inbox UI, seeded notice, and persistence live checks passed. |
| 25 | complete | Celery 7/3/1 reminder task with dedupe history, preference/time/audience-aware broadcasts, manager/admin UI, member-dashboard cards, and audited create/update passed live checks. |
| 26 | complete | Admin-only payment/invoice tables expose member/status/date/plan/tier filters; CRM/billing exports reuse exact active filters and audit PII exports. CSV headers/content and manager denial passed live checks. |
| 27 | complete | Manager/admin audit UI exposes date/action/actor/target/entity filters; role-specific operations navigation and approval queue make separation visible. Manager access plus staff/manager sensitive-area denials passed. |
| 28 | complete | Six centralized integer rules use PostgreSQL persistence, Redis cache/fallback, safe bounds, invalidation, audit, manager/admin UI, and idempotent seed. Metadata and live update checks passed. |
| 29 | complete | Migration `20260716_0005` creates indexed devices/sessions/events with active-session uniqueness. Database is migrated to this head and `alembic check` reports no drift; ERD/route docs are current. |
| 30 | complete | Member QR page uses signed rotating JWT/JTI state, countdown/automatic refresh, effective membership block states, capacity and recent attendance. Valid, expired, invalid, superseded, inactive, and rotation paths passed live checks. |
| 31 | complete | Device-authenticated check-in/out returns stable codes and occupancy without direct database access. Unauthorized-device and all documented token/session failures passed; `docs/api/iot-scanner.md` defines the contract. |
| 32 | complete | CLI and optional Compose profile support valid, invalid, expired, inactive, duplicate, and unauthorized-device scenarios. CLI compilation/help passed and corrected commands are documented. |
| 33 | complete | Redis duplicate guard, locked/unique active-session creation, checkout, reasoned/idempotent manual close, timeout worker/events, and occupancy reconciliation are connected. Live check-in/duplicate/checkout/manual-close passes. |
| 34 | complete | PostgreSQL active count drives capacity percentage; Redis is a 30-second reconciled cache; six thresholds/boundaries are tested; member/admin cards consume the live response. |
| 35 | complete | Member paginated history and staff/manager/admin attendance operations UI expose date/status/member filters, source/device/events, states, and guarded manual close. Member/staff live endpoints passed. |
| 36 | complete | Manager/admin endpoint returns the full 168-cell weekday/hour grid, visits today, busiest hour, and occupancy. Accessible CSS heatmap/KPIs are integrated; manager success and staff denial passed live. |
| 37 | complete | Trainers/classes/bookings/waitlists migration, model constraints, relationships, indexes, minimal trainer seed, ERD, and explicit Day 39-41 boundary are complete and schema-verified. |
| 38 | complete | Admin list/create/update/cancel APIs and schedule UI include filters, side card, RHF/Zod dialog, timezone/future/capacity/trainer/location overlap validation, confirmation/reason, audit, and RBAC. Live CRUD/cancel and manager denial passed. |

## Final verification ledger

- Recovery copy: 211 eligible files copied outside the repository and SHA-256 checked; zero missing/mismatched files.
- Pre-migration dump: PostgreSQL custom-format backup validated by `pg_restore --list` with 60 TOC entries.
- Database: current/head `20260716_0005`; `alembic check` clean; seed twice produces one representative seeded payment/invoice/notification.
- Backend: compileall passed; final run had 43 pytest tests pass in 4.45 seconds, including expiry-reminder dedupe and class-overlap context; lifecycle, reminder, and timeout worker tasks passed sequential same-process execution after adding per-loop engine disposal.
- Frontend: ESLint zero errors/one TanStack compiler warning; production TypeScript/Vite build passed (1,885 modules, about 713 kB main chunk).
- Live API: 23 scanner/attendance passes, 42 operations/RBAC passes, and separate approval-queue, revoked-access, and class-overlap checks passed.
- Legacy regression: 24 live checks passed for registration/uniqueness/verification, login and auth resolution, profile/password/reset flows, plans, purchase/renewal/idempotency, payment/invoice history, PDF download, and member admin denial.
- Deep-link HTTP checks: `/app/qr`, `/admin/members`, `/admin/approvals`, and `/admin/classes` all returned the Vite SPA document with HTTP 200.
- Runtime: API health success, PostgreSQL/Redis healthy, worker/beat/API recreated from the compatible bcrypt image without deleting volumes, frontend live dependency graph synchronized.
- Visual QA limitation: the required in-app browser backend was unavailable and returned an empty browser list. No unrelated controller was substituted. A final interactive responsive/screenshot pass remains recommended, but no implementation day is left partially wired.

## Final scope boundary

Days 39+ remain intentionally unimplemented: full PT management/assignment, member class listing/booking/waitlist/cancellation-window workflows, dashboard work specifically dependent on those later features, Expo/mobile delivery, real payment/refund settlement, physical firmware, and AI/personalization.
