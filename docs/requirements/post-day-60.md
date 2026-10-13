# Post-Day-60 requirements

Created September 20, 2026 and revised September 21, 2026 for the owner-approved YPTrain scope. The BRD identifiers FR1–FR39 remain unchanged. FR40–FR55 were reserved by the first post-Day-60 slice; FR56 is the next unused identifier. The former YPFood meanings for FR45–FR51 are cancelled rather than implemented. Status describes the current repository, not the intended roadmap.

| ID | Requirement | Current status | Planned feature slice |
|---|---|---|---|
| FR40 | Reliable mobile back navigation, session restoration and logout | Verified in Feature 1 on an Android emulator; physical-device and iOS verification remain pending | Feature 1 |
| FR41 | Mobile membership purchase/renewal/cancellation state consistency | Verified across Features 1 and 3, including registration/verification, plans, server-backed membership registration/renewal, invoices, lifecycle requests, live membership/QR/attendance/crowdedness and class booking/waitlists; external card settlement remains unconfigured | Features 1, 3 and current YPTrain operations update |
| FR42 | Upcoming booked-class reminders and notification navigation | Verified for preference-aware deduplicated in-app reminders and booking navigation; device push remains credential/environment gated | Feature 3 |
| FR43 | Individual manager-created staff and trainer accounts | Implemented with manager/admin-only provisioning, one-time strong temporary credentials, required first-login replacement, automatic PT profile linkage and transactional audit | Feature 10 |
| FR44 | Staff clock-in/clock-out records and manager reporting | Implemented with server UTC timestamps, database-enforced one-open-shift rule, own history, manager filters/pagination, gym-timezone rendering and transactional audit | Feature 10 |
| FR45 | Admin machine/exercise catalogue management | Implemented in Feature 5; isolated and client verification recorded in the tracker | Feature 5 |
| FR46 | Upper/lower exercise browse and search | Implemented against one member API on web and Expo | Feature 5 |
| FR47 | Guided exercise logging with 1–10 sets, reps and weight | Implemented on web and Expo against one member API; physical/native-device verification remains pending | Feature 6 |
| FR48 | Attendance-linked workout session per gym-local calendar date | Implemented with server-derived member/date, scanner attendance proof, eligible membership, daily uniqueness and idempotency/concurrency guards | Feature 6 |
| FR49 | Workout history calendar and same-exercise comparisons | Implemented from member-owned attendance/workout snapshots on web and Expo; physical/native-device verification remains pending | Feature 7 |
| FR50 | Weekly front/back muscle heatmap | Implemented with one documented weighted-set-exposure metric, Monday–Sunday gym-local boundary, text legend/list and non-prescriptive disclosure on web and Expo | Feature 7 |
| FR51 | Guarded AI weekly training review | Data-only deterministic weekly balance is implemented on web/mobile; live AI still requires an approved provider and guarded pipeline | Feature 8 |
| FR52 | Live gym equipment/exercise guide | Shared guide implemented; illustrative machine entries do not confirm installation and logging awaits Feature 6 | Feature 5 |
| FR53 | Registration welcome email through configurable SMTP delivery | Provider-neutral development delivery and SMTP adapter verified in Feature 4; live delivery remains credential gated | Feature 4 |
| FR54 | Consistent action success/error feedback and real-time UI refresh | Partially implemented in Features 1–2 and existing connected clients; later mutation corrections remain | Features 1, 2, 10 and 11 |
| FR55 | White-and-green workout-oriented responsive design system | Verified in Feature 2 across shared mobile components/member routes and the web foundation; physical-device and iOS verification remain pending | Feature 2 and later UI slices |
| FR56 | Previous-month attendance-based membership discount | Implemented with owner-approved better-of pricing and first-successful-renewal consumption; isolated backend, web and Expo verification pass | Feature 9 |

## Feature 1 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR40 | `mobile/src/lib/session.ts`, `mobile/src/lib/navigation.ts`, `mobile/src/lib/auth.tsx`, route-aware `PageTop` fallbacks | `mobile/tests/reliability.test.mjs`; mobile typecheck, lint, tests and Android export |
| FR41 | `mobile/src/lib/query.ts`, fresh dashboard reads on membership screens, server-status labels on dashboard/profile/QR/renewal, unchanged server-issued rotating QR | Mobile state-transition test plus backend purchase/idempotency/lifecycle/JWT integration suite |

The current backend has no logout or token-revocation endpoint. Feature 1 therefore clears SecureStore and both web storage fallbacks, removes member-scoped query data and replaces navigation with `/login`; it does not claim server-side access-token revocation. The existing access token remains bounded by its configured expiry.

## Feature 2 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR54 | Semantic mobile loading, empty, error and field-validation states; larger reusable web/mobile controls | Mobile typecheck/lint/tests/export plus connected screen and mutation regression |
| FR55 | `mobile/src/lib/theme.ts`, `mobile/src/components/ui.tsx`, all member routes, Expo light shell, web CSS tokens and shared web buttons | Contrast test, phone/tablet/desktop visual inspection, Android emulator inspection, web lint/build |

## Feature 3 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR41 | Mobile `/register`, `/verify-email`, membership-request/history, attendance-day summary and existing shared member flows | Isolated registration/lifecycle/attendance/QR/payment/booking suites; mobile typecheck, lint, tests and Android export |
| FR42 | Celery minute schedule, configurable lead time, PostgreSQL dedupe key, per-member preferences, notification action metadata and booking deep link | `test_member_reminders.py`, `member-journey.test.mjs`, API ownership checks and full isolated suite |

The default gym timezone is `Asia/Ho_Chi_Minh`, validated as an IANA timezone. Attendance distinct-day aggregation and class reminder presentation use that configured zone. Feature 3 adds persistent in-app reminders only because no device-push service or credentials are configured.

## Feature 4 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR53 | Registration transaction creates one deduplicated PostgreSQL welcome-email intent; Celery sends via development Maildir or configurable SMTP, with bounded retries and private failure logs. Verification/reset messages use the configured transport without changing token hashing or one-time use. | `test_account_journey.py` registration, duplicate, escaped HTML, link/token and retry cases; `test_email_delivery.py` SMTP/auth/configuration checks; full isolated backend suite and normal-stack migration/worker check. External SMTP delivery is not claimed. |

The YPTrain Features 5–9 replace all previously proposed food catalogue, cart, checkout, stock, delivery, review and payment work. No YPFood schema, API or client implementation exists or is planned.

## Feature 10 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR43 | Existing `users` authentication with generated internal login, immediately hashed temporary password, `must_change_password` gate and automatic `personal_trainers` link for PT; manager/admin web workflow at `/admin/staff` | `test_staff_operations.py` covers RBAC, escalation rejection, uniqueness, password secrecy/replacement, PT linkage and audit; web lint/build |
| FR44 | `staff_shifts` with server UTC timestamps, time-order check, partial unique open-shift index, locked clock mutations, self-service `/staff/time-clock` and filtered manager report | Real PostgreSQL concurrent clock-in, own-data/RBAC, clock-out, audit and gym-local date tests; Alembic and web checks |

`STAFF_ACCOUNT_EMAIL_DOMAIN` defaults to the existing local `ypgym.dev` demonstration namespace. It is a login identifier, not a claim that staff mailboxes exist. Shift corrections are not exposed; adding them later requires reasoned before/after audit data.

## Feature 5 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR45 | PostgreSQL training exercises, muscle tags and sanitized images; manager/admin create/edit/archive/restore and same-transaction audit; `frontend/src/features/training/pages/AdminTrainingPage.tsx` | `test_training_catalogue.py` validates RBAC, records, archive, image handling and audit; web lint/build |
| FR46 | Member API search/filter/pagination and upper/lower web + Expo browse/detail screens | Same API contract exercised from both clients; isolated API test and web/mobile type/lint/export checks |
| FR52 | Usage, primary/secondary muscles, safety and illustrative labeling | Seed repeatability test, guide detail and image fallback; physical machine presence remains unconfirmed |

## Feature 6 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR47 | Web and Expo Add Exercise forms with a 1–10 stepper, retained hidden-row values, positive reps, non-negative two-decimal external load, explicit kg/lb unit, bodyweight/zero-load guidance and confirmed server success | `test_workout_logging.py`; web lint/build; mobile typecheck/lint/nine tests/Android export; authenticated web and Expo-web form/session parity |
| FR48 | `workout_sessions`, `workout_exercises`, `workout_sets`; one member/gym-date constraint; attendance FK; scanner event and membership gate; user locking; request-key idempotency; catalogue snapshots | Isolated real PostgreSQL concurrency, denial, checkout, revocation, snapshot and timezone-boundary coverage; Alembic current/check at `20260922_0011` |

Feature 6 permits writes only for the current configured gym-local day. Checkout, timeout and QR expiry leave an already recorded check-in and workout history intact. Editing, deletion and historical backfill are intentionally unavailable; Feature 7 owns historical reads and comparisons.

## Feature 7 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR49 | Member-only paginated activity history, exact day detail and exercise-history APIs; web/Expo contribution calendars distinguish attendance from logged workouts and show snapshotted sets plus descriptive prior-session changes | `test_workout_history.py` covers pagination, account isolation, attended-only days, exact sets, catalogue rename stability and comparison baselines; web build/lint and mobile typecheck/lint |
| FR50 | Current gym-local Monday–Sunday summary; each set contributes 1.0 primary and 0.5 secondary muscle exposure; accessible front/back red map plus raw text list on both clients | Empty week, cross-year week, bodyweight, primary/secondary attribution and calendar/map parity coverage in `test_workout_history.py`; metric contract in `docs/api/workout-history.md` |

Weighted set exposure is descriptive and load-independent: bodyweight/zero-load sets count, while exact reps and kg/lb values remain visible separately. Intensity uses the same 0–4 relative thresholds in each displayed scope. The map does not claim measured anatomical activation, and comparisons do not prescribe a next-session target.

## Feature 8 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR51 data-only preparation | The authenticated weekly muscle-map response includes one backend-derived deterministic balance summary. Web and Expo render the same highest/lower exposure groups with an explicit **not AI-generated** disclosure. | `test_workout_history.py` covers populated and empty summaries; the isolated PostgreSQL/Redis suite plus web/mobile checks pass. |
| FR51 live guarded AI | Not implemented. No approved provider, provider key/configuration, rate-limited guarded pipeline or released FR39 chatbot exists. | Remains decision gated; no template is labelled as AI-generated. |

## Feature 9 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR56 | Member-only previous-complete-month quote from distinct gym-local `iot_scanner` dates; 80% threshold; better of plan discount or 10%; first successful renewal consumes the month; failed/cancelled/expired payment releases it; PostgreSQL reservation uniqueness and immutable payment/invoice snapshots | `test_attendance_benefit.py` and integration coverage for month boundaries, thresholds, zero attendance, source/deduplication/privacy, frozen coverage, both discount orders, replay/concurrency, mock/VNPay paths and invoice state; full isolated suite and web/mobile builds pass |

The full calculation and state contract is `docs/api/attendance-renewal-benefit.md`. The server derives member identity, attendance, price and final discount; neither web nor Expo submits those values.
