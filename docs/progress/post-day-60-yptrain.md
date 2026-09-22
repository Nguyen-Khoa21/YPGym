# Post-Day-60 mobile and YPTrain tracker

Updated September 22, 2026. This tracker covers the owner-approved post-Day-60 YPTrain roadmap. The completed Day 42–60 release remains recorded separately in `day-43-60-tracker.md`.

## Discovery baseline

- Repository: `C:\Users\Admin\ypgym`, branch `main`, upstream `origin/main`, remote `https://github.com/Nguyen-Khoa21/YPGym.git`.
- Feature 3 resumed from synchronized local/remote commit `bc5a6bd44ab6f52fc0c939ffd4ebd1d5dd499416`; annotated release tag remains `v0.60.1` on the earlier checkpoint.
- No merge or rebase state was present. User-owned `README.md`, `RUN_GUIDE.md` and `tmp/` work was preserved and excluded from this slice.
- Alembic is at `20260921_0008 (head)` and `alembic check` reports no new upgrade operations. Normal PostgreSQL/Redis dependency health is `ok`.
- Fresh web baseline: lint passed with the existing TanStack Table React Compiler warning; production build passed with the existing 739.63 kB bundle warning.
- Fresh mobile baseline before editing: typecheck, lint, two QR tests and Android export passed. Expo Doctor reported 20/21 because four installed SDK 57 packages are one patch behind current compatibility recommendations: `@expo/ui`, `expo`, `expo-constants` and `expo-router`. No dependency was silently upgraded in Feature 1.
- Feature 2 final evidence is current: isolated backend **102 passed with five existing Starlette deprecation warnings in 51.80 seconds**; Compose/Alembic checks are clean; mobile typecheck/lint, seven Node tests and Android export pass; web lint/build pass with existing warnings. Expo-web phone/tablet/desktop review and native Android login/four-tab accessibility-tree navigation passed. Physical phone, iOS and human UAT remain unverified.
- Feature 3 final evidence: isolated PostgreSQL/Redis migrations through `20260921_0008` and **105 backend tests passed with five existing warnings in 45.05 seconds**. Mobile typecheck/lint, nine Node tests and Android export pass; web lint/build pass with existing warnings. Authenticated Expo web confirmed registration validation, API-online login, lifecycle-request history/forms, gym-local visit totals and the class-reminder preference. Device push, physical phone, iOS and human UAT remain unverified.
- Feature 4 is implemented locally after Feature 3 reached `origin/main` at `e7f5d76`. The fresh isolated migration/test run and normal development-stack migration/worker check are recorded in `docs/release/integration-report.md`. Live SMTP credentials and sender have not been supplied; external delivery is unverified.

## Existing dependency map

| Capability | Mobile/web client | API/service/repository/state |
|---|---|---|
| Authentication/session | Mobile `auth.tsx`; web `AuthContext`/`ProtectedRoute` | `/auth/register`, `/verify-email`, `/login`, `/me`, forgot/reset; `AuthService`, token/user repositories, PostgreSQL JWT identity; no logout endpoint |
| Membership and billing | Mobile dashboard/renew/invoices; web membership/billing pages | `/membership-plans`, `/memberships/purchase`, lifecycle request/admin decision routes, `/billing/me/*`; membership/billing services and repositories; PostgreSQL transaction plus immutable invoice metadata |
| Attendance and QR | Mobile dashboard/QR/attendance; web member/operations attendance | `/attendance/qr-token/me`, member/admin attendance, scanner and crowdedness routes; PostgreSQL source of truth and Redis short-lived QR/occupancy state |
| Classes and trainers | Mobile classes/bookings; web member/admin/PT pages | class/trainer/booking/waitlist routes; class/trainer services and repositories; PostgreSQL row locking and waitlist rules |
| Notifications/broadcasts | Mobile inbox/preferences/dashboard; web member/manager pages | notification/preference/broadcast routes; `NotificationService`; PostgreSQL records and Celery expiry-reminder schedule |
| UI feedback/cache | React Native alerts/messages and TanStack Query; web Sonner and TanStack Query | Per-feature query keys and mutation invalidation; Feature 1 centralizes member session cleanup and membership refresh roots |
| Registration email | Web and native registration/verification | `AuthService` preserves one-time verification/reset links; PostgreSQL stores one welcome intent per new member; Celery uses ignored Maildir in development or configurable SMTP. External SMTP delivery remains unverified. |

## Feature slices

| Slice | Requirement IDs | Status | Evidence / boundary |
|---|---|---|---|
| 1. Mobile reliability and membership state | FR40, FR41, part of FR54 | Verified | Session/navigation/state code; 102 backend tests, six mobile tests, typecheck/lint/export and Android logout/restart journey pass |
| 2. White/green workout design system | FR54–FR55 | Verified | Shared semantic tokens/components cover all named mobile screens; web foundation aligned; contrast, responsive web, native Android navigation, automated checks and export pass |
| 3. Complete mobile journey and class reminders | FR41, FR42 | Verified | Shared API registration/verification and lifecycle requests; preference-aware deduplicated PostgreSQL reminders with booking targets; gym-local visit days; 105 backend and nine mobile tests plus lint/typecheck/build/export |
| 4. Welcome email | FR53 | Development verified; live delivery unverified | Transactional one-per-member intent, worker retry/dedupe, Maildir and SMTP adapter; normal migration and empty-queue worker probe pass. Sender credentials are owner-controlled. |
| 5. YPTrain catalogue and equipment guide | FR45, FR46, FR52 | Not started | Requires forward migration, catalogue RBAC and shared web/mobile API |
| 6. Attendance-linked workout logging | FR47–FR48 | Not started | Requires attendance ownership gate, daily uniqueness and normalized sets |
| 7. History, comparisons and muscle map | FR49–FR50 | Not started | Metric/week definition must be consistent across both clients |
| 8. Guarded weekly training review | FR51 | Decision gated | No approved provider or existing guarded FR39 pipeline has been verified |
| 9. Attendance renewal discount | FR56 | Decision gated | Combination and one-time consumption policy require owner approval |
| 10. Staff accounts and time clock | FR43, FR44 | Not started | Requires migration, RBAC, audit and first-login policy |
| 11. Management UX corrections | FR43, FR54–FR55 | Not started | Reuses the current Sonner/query patterns and Feature 10 accounts |
| 12. Integrated regression and release checkpoint | FR40–FR56 | Not started | Begins only after all functional slices and push gates |

## Scope controls

- Each slice is committed separately and waits for explicit push permission before the next slice starts.
- YPFood catalogue, cart, checkout, stock, shipping, review and payment functionality is cancelled and must not be introduced.
- FR39 remains deferred. Feature 8 is a narrower guarded weekly review and cannot become live AI without an approved provider and safety pipeline.
- YPTrain history is descriptive and must not provide medical, injury, diet, rehabilitation or automatic next-workout prescriptions.
- Live payment, SMTP credentials, Expo push credentials, public deployment and app-store release remain credential or environment gated.
- Physical phone, iOS and human UAT are not inferred from emulator, export or automated checks.
- The openGym repository was reviewed only for product inspiration around equipment-aware search, bodyweight/load semantics, preserving entered set state, contribution calendars and accessible muscle maps. YPGym will implement these ideas within its existing architecture; no openGym code or media is copied because its repository is AGPL-3.0 and its exercise data/media carry separate terms.
