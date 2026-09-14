# YPGym Codex Handoff

## 2026-09-14 session closeout

The authoritative continuation handoff is [`docs/HANDOFF.md`](docs/HANDOFF.md). This root file records the closing summary for today.

- Mobile implementation is present in `mobile/src/` with Expo Router, SecureStore sessions, dashboard, rotating QR, classes/booking/waitlist, bookings, attendance, notifications/preferences, profile, invoices, and simulated renewal. Mobile typecheck/lint/QR tests/Android export passed; native authenticated screenshots remain open because no emulator app was available.
- Expo web connectivity was fixed: local web uses `http://localhost:8001/api/v1`, Android emulator uses `10.0.2.2`, and physical phones use the LAN address. Backend CORS explicitly allows local Expo web origins and focused CORS checks pass 2/2.
- Backend work today added analytics, UTC/uniqueness corrections, atomic Redis rate limits, JWT/QR purpose separation, revoked-membership renewal denial, privacy-safe errors/logging, and ignored development mail outbox handling.
- The isolated PostgreSQL/Redis run passed 94 tests with 4 warnings; the normal development suite passed 64 and skipped 27 integration cases outside the isolated environment. The benchmark stored 1,000 users and related membership/class/attendance data; read probes were 100% successful and login rate limits remained enabled.
- Current release work is uncommitted after pushed baseline `bcec6b9`. Suggested session commit title: `feat: add analytics security hardening and Expo web connectivity`.

Last updated: 2026-07-02

## Current Repo State

- Project root: `C:\Users\Admin\ypgym`
- Git branch: `main`
- Git remote: `origin` -> `https://github.com/Nguyen-Khoa21/YPGym.git`
- Current milestone: Day 11 to Day 20 completed
- Main plan file: `YPGym_60_Day_Development_Plan_Revised_PostgreSQL (1).md`
- BRD/design reference: `FYP Brief BRD - Anh Khoa - Design Architecture.docx`
- Current Alembic head: `20260702_0003 (head)`

The repo now contains the Day 5-10 PostgreSQL foundation plus the Day 11-20 authentication, membership, and billing feature slice.

The older Day 1-4 scaffold containers may still appear in Docker Desktop or `docker compose ps`. They were left untouched. The revised stack uses `5174`, `8001`, `5433`, and `6380` to avoid conflicts with the older scaffold.

## 2026-07-15: Frontend Redesign And API Reintegration Pass

- Branch: `main`
- Baseline commit: `4b6f94c` (`Implement auth membership billing slice`)
- Working tree status at handoff: redesign changes are uncommitted.
- Figma references used: `Untitled` (`XQ3HBuKBg9NpLxCqoCwUb9`), Page 1, `Membership Policies` frame `1:2`, and `Member Profile` frame `1:4176`.

### What Changed

- Replaced the generic public chrome with a responsive `AppFrame`, a public hero, an authentication shell, policy content layout, custom not-found page, and a permission-denied route.
- Added the Figma-informed `MemberShell`: desktop member sidebar plus mobile bottom navigation. The profile preserves the Figma settings/menu hierarchy and labels unconnected personalization and notification rows honestly.
- Added `AdminShell` patterns for billing, CRM, attendance, classes and PT assignment routes. Only admin billing is connected; no CRM records or other admin data are mocked.
- Redesigned register, login, forgot/reset password, email verification callback/success, plans, purchase/review/success, profile, member billing, member dashboard, admin dashboard/billing, and the PT safe placeholder.
- Added `/policies/membership` using the Figma policy-table-of-contents structure and the sections: Renewal & Expiry, Freeze Eligibility, Cancellation, Refunds & Credits and QR Check-in Rules.
- Added canonical application routes while retaining aliases:
  - `/member` -> `/app/dashboard`
  - `/profile` -> `/app/profile`
  - `/billing` -> `/app/billing`
  - `/pt` -> `/pt/dashboard`
- Added explicit planned routes for QR, class booking, CRM, attendance, class administration and PT assignments. They show planned development days instead of simulated feature data.

### API And State Details

- `apiRequest` now accepts `AbortSignal` for route-query cancellation and broadcasts `ypgym:unauthorized` on `401`; `AuthProvider` centrally clears stale sessions.
- Profile is now loaded with `GET /users/me` and persisted with `PATCH /users/me`; name/phone validation, blocked email editing, current-password validation and backend errors remain visible.
- Purchase retains its one-per-page idempotency key. Successful purchases invalidate billing and dashboard query groups.
- Purchase success distinguishes a renewal when the returned invoice coverage start differs from the membership start.
- Invoice downloads now handle a failed request in-page instead of allowing an unhandled promise rejection.

### Design System

- Tokens: cream background, forest primary, lime secondary, coral accent, Barlow Condensed display typography and Manrope UI typography.
- Reusable layouts: `AppFrame`, `AuthShell`, `MemberShell`, `AdminShell`.
- Reusable route states: loading, error, permission denied, not found, and intentionally unavailable future features.

### Files Modified Or Added

Frontend:

- `frontend/src/index.css`
- `frontend/src/app/router.tsx`
- `frontend/src/app/pages/*`
- `frontend/src/components/layout/AppFrame.tsx`
- `frontend/src/components/layout/AuthShell.tsx`
- `frontend/src/components/layout/MemberShell.tsx`
- `frontend/src/components/layout/AdminShell.tsx`
- `frontend/src/components/ui/Form.tsx`
- `frontend/src/lib/apiClient.ts`
- `frontend/src/features/auth/*`
- `frontend/src/features/member/pages/*`
- `frontend/src/features/memberships/pages/*`
- `frontend/src/features/billing/pages/PaymentHistoryPage.tsx`
- `frontend/src/features/admin/pages/*`

Documentation:

- `docs/design/route-screen-map.md`
- `README.md`
- `handoff.md`

Backend:

- No backend source or schema changes. Day 11-20 API contracts were preserved.

Dependencies:

- None added or removed. TanStack Query was already installed and remains the query/mutation layer.

### Verification Performed On 2026-07-15

Passed:

```powershell
cd C:\Users\Admin\ypgym\frontend
npm run lint
npm run build

cd C:\Users\Admin\ypgym
docker compose --profile app up -d --build
docker compose --profile app exec -T backend-api alembic -c alembic.ini current
Invoke-RestMethod http://localhost:8001/api/v1/health
Invoke-RestMethod http://localhost:8001/api/v1/health/dependencies
python -m compileall backend\app
```

- Alembic reports `20260702_0003 (head)`.
- Health returned `YPGym API is running`; database and Redis dependency health both returned `ok`.
- The initial combined Docker/migration command exceeded the two-minute command timeout after containers started; rerunning migration, health and compile as separate commands passed.
- Functional API flow passed with a new member account: registration, duplicate email/phone `409`, development-log verification, login and `/auth/me`, `GET/PATCH /users/me` with password change, six plans, purchase, duplicate idempotency replay, renewal, payment/invoice history, invoice PDF `200`, member token rejection from admin billing `403`, forgot/reset password, reset-token reuse `400`, and login with the new password.
- Browser checks passed with no console errors: desktop home, 1280px policy layout, 390px member profile, refreshed `/app/profile` deep link, 768px profile/policy checks, and member navigation to `/admin/billing` redirecting to `/permission-denied`.

Visual limitation:

- Desktop home, desktop policy and mobile profile screenshots were captured in the in-app browser. The browser declined one narrow-policy screenshot capture; the 768px DOM layout and console state were still checked successfully.

### Known Limitations

- Figma MCP hit its Starter-plan call limit after the policy/profile structural inspection. No additional Figma asset export or frame-specific review was possible in this pass.
- The accessible Figma file did not include supplied frames for the public/auth, purchase, billing, admin or PT routes. Those use the documented shared design system, not asserted pixel-perfect parity.
- Google Fonts are loaded at runtime for the display/UI typography. The local system stack is used if the font request is unavailable.
- The Vite production build passes with the existing warning that the main JavaScript chunk is over 500 kB.
- The old Day 1-4 orphan containers remain visible, including a restarting `ypgym-backend`; the current stack is `ypgym-backend-api` and `ypgym-frontend-web`.
- QR attendance, crowdedness, classes, broadcasts, notifications, CRM, cancellation/freeze approvals, full admin billing, PT assignments and Expo mobile remain deferred. No backend behavior was fabricated for them.

### Manual Test Steps

1. Start the stack with `docker compose --profile app up -d --build` and open `http://localhost:5174`.
2. Register at `/register`; submit a duplicate email or phone to view inline backend errors.
3. Use `docker compose --profile app logs backend-api` and open the `development_email_verification_link` at `/verify-email?token=...`.
4. Log in at `/login`; member accounts land on `/app/dashboard`, while staff/admin/manager and PT accounts land on their role destinations.
5. Open `/app/profile`, update name/phone, then supply the current and new password to verify the account-security path. Email remains read-only.
6. Open `/memberships`, choose a plan, confirm the mock payment once, then open `/app/billing` to download its invoice.
7. Refresh `/app/profile` or paste it into a new tab while signed in; the profile remains protected and loads after auth resolution.
8. As a member, paste `/admin/billing`; the app should show `/permission-denied`.

### Recommended Next Development Day

Start Day 21: membership lifecycle, freeze eligibility/approval and expiry worker. The policy screen and planned states now provide an honest UI foundation for that work.

## What Was Implemented Today

### Day 11: Core PostgreSQL Models and Migrations

Added SQLAlchemy models and Alembic migrations for:

- `users`
- `email_verifications`
- `password_resets`
- `membership_plans`
- `user_memberships`
- `system_configurations`
- `payments`
- `invoices`

Migration files:

- `backend/alembic/versions/20260702_0002_core_auth_membership.py`
- `backend/alembic/versions/20260702_0003_billing.py`

Important database behavior:

- UUID primary keys.
- `created_at` and `updated_at` timestamps where appropriate.
- Unique `users.email` and `users.phone`.
- Indexed email, phone, user ID relationships, membership status, and expiry date.
- Hashed email verification and password reset tokens.
- Payment idempotency via unique `(user_id, idempotency_key)`.
- Invoice metadata is immutable after creation.

### Day 12 to Day 15: Auth Flows

Backend:

- `POST /api/v1/auth/register`
- `GET /api/v1/auth/verify-email?token=...`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`

Implemented:

- Password hashing with `passlib` and bcrypt.
- `bcrypt<5` pin because `passlib==1.7.4` is not compatible with bcrypt 5.x.
- JWT access tokens with user ID, role, tier, and expiry.
- Current-user dependency and role guard helpers.
- Development-only verification and reset links logged by backend.
- Neutral forgot-password response.
- One-time-use verification and reset tokens.

Frontend:

- `/register`
- `/verify-email`
- `/verify-email/success`
- `/login`
- `/forgot-password`
- `/reset-password`
- Protected route wrapper and auth context.

### Day 16: Profile Settings

Backend:

- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`

Implemented:

- Member can update `name` and `phone`.
- Duplicate phone is rejected.
- Password change requires current password.
- Email change is intentionally blocked for now because it needs a re-verification workflow.
- Audit log TODO added for later sensitive-account-change tracking.

Frontend:

- `/profile`
- Profile form with inline validation, success toast, and account security section.

### Day 17 and Day 18: Membership Plans and Seed Data

Backend:

- `GET /api/v1/membership-plans`
- Idempotent seed command:

```powershell
docker compose --profile app exec backend-api python -m app.db.seed
```

Seeded plans:

- 1 Month
- 3 Months
- 6 Months
- 1 Year
- 2 Years
- 3 Years

Seeded system configuration:

- gym capacity
- QR token TTL
- attendance timeout
- duplicate scan window
- class cancellation window
- waitlist size

Frontend:

- `/memberships`
- Responsive plan cards with price, discount, benefits, and auth-aware CTA.

### Day 19: Mock Membership Purchase and Renewal

Backend:

- `POST /api/v1/memberships/purchase`

Implemented:

- Verified member requirement.
- Backend-owned price calculation.
- Mock payment confirmation.
- Idempotency key duplicate-submit protection.
- New membership starts today when none exists.
- Renewal extends from current expiry when active.
- Payment record creation.

Frontend:

- `/memberships/buy/:planId`
- Mock payment confirmation state and success state.

### Day 20: Invoice and Billing History

Backend:

- `GET /api/v1/billing/me/payments`
- `GET /api/v1/billing/me/invoices`
- `GET /api/v1/billing/me/invoices/{id}`
- `GET /api/v1/billing/admin/payments`

Implemented:

- ReportLab invoice PDF generation.
- Invoice metadata stored in PostgreSQL.
- Invoice PDF download endpoint.
- Member payment/invoice history.
- Lightweight admin billing placeholder endpoint.

Frontend:

- `/billing`
- Member dashboard payment/invoice summary cards.
- `/admin/billing` placeholder table for staff/manager/admin roles.
- `/pt` safe placeholder route for PT login redirect.

## Important Files Created or Modified

Backend:

- `backend/app/models/*.py`
- `backend/app/schemas/*.py`
- `backend/app/repositories/*.py`
- `backend/app/services/*.py`
- `backend/app/api/v1/endpoints/*.py`
- `backend/app/core/dependencies.py`
- `backend/app/db/seed.py`
- `backend/app/utils/security.py`
- `backend/requirements.txt`

Frontend:

- `frontend/src/features/auth/*`
- `frontend/src/features/member/pages/ProfileSettingsPage.tsx`
- `frontend/src/features/memberships/pages/*`
- `frontend/src/features/billing/pages/PaymentHistoryPage.tsx`
- `frontend/src/features/admin/pages/AdminBillingPage.tsx`
- `frontend/src/components/ui/*`
- `frontend/src/lib/apiClient.ts`
- `frontend/src/lib/format.ts`
- `frontend/src/types/api.ts`
- `frontend/src/app/router.tsx`
- `frontend/src/components/layout/AppFrame.tsx`

Docs:

- `README.md`
- `docs/design/route-screen-map.md`
- `docs/database/erd.md`
- `handoff.md`

## How To Run

From PowerShell:

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app up -d --build
docker compose --profile app exec -T backend-api alembic -c alembic.ini upgrade head
docker compose --profile app exec backend-api python -m app.db.seed
```

Open:

```text
Frontend:      http://localhost:5174
Swagger docs:  http://localhost:8001/docs
Backend API:   http://localhost:8001/api/v1
PostgreSQL:    localhost:5433
Redis:         localhost:6380
```

## How To Verify Email in Development

SMTP is not configured. Verification links are written to backend logs.

After registering, run:

```powershell
docker compose logs backend-api | Select-String "development_email_verification_link" | Select-Object -Last 1
```

Open the printed URL, for example:

```text
http://localhost:5174/verify-email?token=...
```

## How To Check PostgreSQL

```powershell
docker compose exec postgres-db psql -U ypgym -d ypgym
```

Useful SQL:

```sql
\dt

SELECT id, name, email, phone, role, tier, is_email_verified, created_at
FROM users
ORDER BY created_at DESC
LIMIT 10;

SELECT name, duration_days, base_price, discount_percent, is_active
FROM membership_plans
ORDER BY duration_days;

SELECT id, user_id, amount, status, mock_reference, created_at
FROM payments
ORDER BY created_at DESC
LIMIT 10;

SELECT invoice_number, user_id, amount, pdf_path, created_at
FROM invoices
ORDER BY created_at DESC
LIMIT 10;
```

GUI connection:

```text
Host: localhost
Port: 5433
Database: ypgym
Username: ypgym
Password: ypgym_dev_password
```

## Verification Performed

Passed:

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app up -d --build
docker compose ps
docker compose --profile app exec -T backend-api alembic -c alembic.ini current
Invoke-RestMethod http://localhost:8001/api/v1/health
Invoke-RestMethod http://localhost:8001/api/v1/health/dependencies
python -m compileall backend\app
```

Frontend:

```powershell
cd C:\Users\Admin\ypgym\frontend
npm run lint
npm run build
```

Manual API flow passed:

- Register new user.
- Duplicate email rejected.
- Duplicate phone rejected.
- Verify email via local dev log link.
- Login and receive JWT.
- `/auth/me` works with JWT.
- Member token rejected from admin billing endpoint.
- Forgot password creates reset link in logs.
- Reset password works.
- Reset token cannot be reused.
- Login works with new password.
- Profile name/phone update works.
- Membership plans return 6 seeded plans.
- Mock membership purchase works.
- Duplicate purchase request returns original payment.
- Payment history returns payment.
- Invoice history returns invoice.
- Invoice PDF download works.

HTTP checks:

```powershell
curl.exe -I http://localhost:5174
curl.exe -I http://localhost:8001/docs
```

Both returned `200 OK`.

## Known Caveats

- Old Day 1-4 containers still appear as orphans. They were not removed.
- `docker compose ps` may show old `ypgym-backend`, `ypgym-frontend`, `ypgym-mongodb`, and `ypgym-redis`.
- Development verification/reset links are logged, not emailed.
- Browser automation tool failed with `sandboxCwd must use the file URI scheme`; page serving was verified with `curl.exe`.
- Docker frontend build reported existing npm audit vulnerabilities. Package upgrades were not attempted during this Day 11-20 slice.
- Full admin billing, CRM, attendance, QR scanning, freeze/cancellation workflows, notifications, class booking, AI chatbot, and Expo mobile screens are not implemented yet.

## Recommended Next Session

Start Day 21 from the revised plan.

Likely next direction: attendance and QR foundation, only if that matches Day 21 in the plan. Do not jump to AI chatbot, full CRM, class booking, notifications, or cancellation approval unless explicitly requested.

## 2026-07-22: Days 39-42 Continuation

This root file remains historical context; `docs/HANDOFF.md` is the current handoff.

- Starting branch/commit: `main` at `de64c1e`; initial user-owned plan/instruction changes were preserved and backed up outside the repository.
- Day 37 schema and Day 38 admin class CRUD passed migration, test, live API, permission, seed, and deep-link prerequisite checks without repair.
- Migration `20260722_0006` adds only the proven missing trainer `bio` and `availability_summary` fields.
- Day 39 adds audited manager/admin trainer profile maintenance, member-safe cards, batched upcoming assignments, and blocked deactivation until future classes are reassigned.
- Day 40 adds membership-aware upcoming classes and class-row-locked booking; a real concurrent capacity race produced one `200`, one `409`, and one confirmed booking.
- Day 41 adds configured inclusive cancellation, My Bookings, deterministic waitlist join/leave, atomic earliest-eligible promotion, ineligible-entry skipping, and deduplicated preference-aware notifications. Concurrent repeat cancellation produced one promoted booking.
- Day 42 adds the typed member-only `/api/v1/dashboard/me` composite and replaces the prior multi-query dashboard with real membership/QR, crowdedness, bookings/waitlists, notification, broadcast, and quick-action states. Its bounded preview now returns the three most recent unread in-app notifications and the live PostgreSQL/API parity check passes. Final acceptance is still partial only because interactive responsive QA remains unavailable.
- Final focused verification: 58 backend tests pass, compileall passes, Alembic is at clean head `20260722_0006`, frontend lint has zero errors/one known warning, and the production build passes.
- Final broad live regression also passed registration/conflicts/verification/reset/profile, purchase/renewal/idempotency/invoices, role boundaries, rotating QR and scanner check-in/out/duplicate protection, crowdedness reconciliation, the 168-cell heatmap, CRM/billing CSV exports, and eight protected SPA deep links. The timeout task ran successfully with zero stale sessions.
- Interactive browser screenshots were not possible because no browser backend was available; this limitation is not represented as a pass.

Run and demo instructions are in `README.md` and `docs/demo/day-39-42-demo.md`; contracts and business rules are in `docs/api/classes-booking-dashboard.md`.

Resume with interactive responsive QA for `/app/dashboard`, `/app/classes`, `/app/bookings`, and `/admin/pt-assignments` when a browser backend is available. The 2026-07-23 retry returned no available browsers. Start Day 43 only after this checkpoint passes.

## 2026-07-23: VND Billing Localization

- Migration `20260723_0007` converts the six plan prices and existing mock payment/invoice values using the fixed project rate of 6,000 VND per former RM unit.
- The shared web formatter now uses `vi-VN`/`VND`, new seeds use VND prices, and invoice downloads regenerate PDFs with grouped `VND` amounts.
- Database backup before conversion: `C:\Users\Admin\.codex\backups\ypgym-vnd-20260723\ypgym-before-vnd.dump`.
- Verification: 59 backend tests pass, frontend lint/build pass with the existing warnings, Alembic is clean at `20260723_0007`, and the downloaded invoice contains VND values with no RM label.

## 2026-09-07: Day 42 gate continuation

The September continuation is tracked in `docs/HANDOFF.md` and `docs/progress/day-43-60-tracker.md`; this section keeps the root handoff resumable as historical context.

- Starting state was preserved at `main`/`69dcb8b`. No reset, clean, stash, commit, tag, push, or destructive database cleanup was performed. Existing user-owned edits and deletions remain in the working tree.
- Docker Desktop was restarted without removing existing containers or volumes. The revised Compose stack is running on the documented ports (web `5174`, API `8001`, PostgreSQL `5433`, Redis `6380`).
- Fresh verification completed: Compose configuration, Alembic current/check, the backend suite (`59 passed`), frontend lint (zero errors plus the existing TanStack warning), frontend production build (existing bundle-size warning), VND plan values, and authenticated invoice PDF regeneration with no RM label.
- The in-app browser became available and the Day 42 responsive checkpoint was exercised across `/app/dashboard`, `/app/classes`, `/app/bookings`, and `/admin/pt-assignments` at desktop, tablet, and phone widths. Evidence is stored under `docs/design/evidence/day-42/`.
- Browser checks covered real dashboard membership/QR states, class search and empty state, booking and cancellation confirmation, My Bookings empty/populated states, role denial, trainer creation/edit/validation/deactivation, loading states, API failure/retry states, and mobile navigation. Disposable QA records are named `QA Empty September`, `Day 42 Browser QA September`, and `QA Trainer September` so they can be identified and removed later without touching seeded records.
- Defects fixed during the checkpoint: dashboard cards now stack until the wide breakpoint, native confirmation dialogs replace unreliable `window.confirm` calls, modal errors render inside the dialog, trainer form labels are associated with controls, and signed-in mobile navigation exposes the role-appropriate workspace links. Auth login/logout now clears user-specific TanStack Query data to prevent account leakage.
- Day 43 remains gated until the rendered checkpoint evidence is indexed and marked verified in the tracker. The next implementation boundary is the Expo/TypeScript member app using the existing shared API; FR39 chatbot, personalization, and recommendations remain explicitly deferred.
- A Playwright development dependency was added for repeatable UI regression coverage; its browser install was started, but the automated suite has not yet been recorded as passing in this handoff. Do not claim Day 43 or final release readiness until that test slice and the remaining Day 43–60 gates are complete.

## 2026-09-13: Mobile member app continuation

This entry records today's continuation from the Day 42 gate. Existing user-owned edits, deletions, Docker volumes, QA records, and the uncommitted working tree were preserved. No commit, reset, clean, stash, push, or destructive database operation was performed.

- Day 42 is verified and indexed in `docs/design/evidence/day-42/README.md`. The four web routes were exercised at desktop, tablet, and phone widths with real member/manager data and loading, empty, error, authorization, booking, cancellation, and trainer-management states. The latest browser checks found no document-width overflow.
- A new Expo SDK 57 member app now lives in `mobile/`. It uses the existing FastAPI contracts and TanStack Query rather than a second backend. The app has secure native token storage with a web fallback, member-only login and role rejection, session restoration, account-switch cache clearing, and 401 logout behavior.
- Implemented member UI and functions: live dashboard, membership status and eligibility, server-issued expiring QR check-in with foreground/background and expiry guards, class search/day filters, booking and waitlist confirmation, bookings and waitlist cancellation, attendance history, notifications/read-all, notification preferences, profile and password update, invoices, plan selection, explicitly simulated mock renewal with an idempotency key, server-verified renewal success, logout, and native dark/lime tab navigation.
- Added a branded YPGym icon and splash assets, web favicon/manifest/theme metadata, and updated `README.md` and `mobile/README.md` with Windows PowerShell setup instructions for an Android emulator and a physical phone. The emulator uses `10.0.2.2:8001`; a phone uses the computer's LAN IPv4 address.
- Mobile verification completed: `npm run typecheck` passed; `npm run lint` passed after adding the Expo ESLint configuration; `npm test` passed with 2 QR safety tests; `npx expo-doctor` passed all 21 checks; `npx expo install --check` passed; and `npx expo export --platform android` produced an Android bundle. The Expo SDK 57 reference was checked against the official versioned documentation.
- The Android AVD `Medium_Phone_API_36.1` is running with Expo Go `57.0.9`. Native launch reached the branded login screen and displayed `Gym API online`; screenshots are in `docs/design/evidence/day-47-mobile/`. Automated credential entry returned the backend's invalid-email-or-password response, so the authenticated native dashboard/QR flow is still unverified and must be repeated with a manually entered or otherwise confirmed seed credential.
- The existing web checks remain green: backend suite `59 passed`, frontend production build passed, and frontend lint has zero errors with the existing TanStack React Compiler warning. The web build retains its existing large-bundle warning. Mobile `npm audit --omit=dev` reports 14 moderate transitive advisories; no forced upgrade was applied because it would risk the Expo SDK 57 dependency set.
- No database models, migrations, constraints, or stored data were changed for the mobile work. Mobile renewal remains a local mock-payment path; no live settlement, store publishing, physical scanner firmware, chatbot, recommendations, or personalization was added.

### Exact resume checkpoint

1. Confirm the seeded member credential manually in the running Android emulator and complete native login, dashboard, check-in QR, class, and profile screenshots. If the seed password has changed, rerun the idempotent seed or use a disposable verified member account; do not use a real payment account for QA.
2. Update `docs/progress/day-43-60-tracker.md` with the completed Day 43–45 work and mark Day 47 only after the authenticated native screens are captured and reviewed.
3. Continue the remaining Day 46–60 release gates; mobile completion does not establish final release readiness.

### Mobile run entry point

Follow `mobile/README.md`. The shortest emulator path is:

```powershell
docker compose --profile app up -d --build
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api python -m app.db.seed
cd mobile
Copy-Item .env.example .env
npm ci
npm run android
```

## 2026-09-14: Isolated release verification continuation

The current authoritative handoff is `docs/HANDOFF.md`. This historical root file now records the latest checkpoint only.

- Uncommitted release work remains on `main` after pushed commit `bcec6b9`; no normal volumes or development records were reset.
- The isolated stack passed 94 tests with 4 warnings; the ordinary development suite is 64 passed, 27 skipped. Real coverage now includes auth/roles/membership, attendance/QR/device/timeout, booking/billing/audit, analytics, and security boundaries. See `docs/release/integration-report.md`.
- A disposable benchmark stored 1,000 users, memberships, classes/bookings, and attendance records. Read probes were 100% HTTP 200; login was 60 HTTP 200 and 940 intentional HTTP 429 under the IP limiter. See `docs/release/performance-report.md`.
- Remaining release gates are native authenticated screenshots/shared-backend rehearsal, Day53 export/config checks, Day54 query review, Day55 final security review, Day56 rendered QA, archive, local commit/tag, and missing academic/UAT evidence.

## 2026-09-14: Manager analytics continuation

This historical root handoff now points to the current `docs/HANDOFF.md` entry above and records the next development batch.

- Last pushed commit: `bcec6b9` on `main`, already pushed to `origin/main` after explicit user authorization. The analytics batch is currently uncommitted; the untracked temporary `tmp/` extraction directory remains.
- Added manager/admin-only `/api/v1/admin/analytics/summary`, using the existing FastAPI endpoint → service → repository pattern. It reads PostgreSQL membership, class booking, attendance, and successful payment records, limits ranges to 366 days, and caches normalized ranges in Redis for 60 seconds.
- The web attendance operations screen now shows persisted manager summary cards and membership/class tables alongside the existing peak-hours heatmap. Staff receives 403 from the summary endpoint.
- Live smoke evidence: manager summary returned data, a repeated request returned `cache_hit=true`, and staff access returned HTTP 403. Backend tests pass `60`, Alembic drift is clean, frontend build passes, and backend compileall passes.
- Day55 security slice adds Redis fixed-window limits for login, password-reset requests, and scanner check-in/out. Unit tests cover 429 and Redis-unavailable behavior; live invalid-login, forgot-password, and scanner probes reached each documented 429 boundary. The security policy is in `docs/policies/security.md`.
- Day50/57/58 release artifacts now include the feature-freeze/backlog, bug list, requirements traceability, blank UAT checklist, research-evidence inventory, viva notes, and examiner demo script. Missing proposal/UAT/research artifacts are explicitly recorded rather than inferred.
- Day54 now has `backend/scripts/load_smoke.py` and `docs/release/performance-report.md`; the recorded run covered 1,000 synthetic logins and authenticated crowdedness/class-list probes with percentile metrics and one transport error documented.
- Day59 disposable Compose rehearsal passed on separate ports and volumes; migrations, seed, health, web shell, manager analytics cache, and member dashboard checks all passed. Its resources were removed without touching the normal stack. The Expo client was not pointed at the temporary API port.
- The current computer-use surface exposed no emulator app, so authenticated native screenshots were not claimed; the existing launch/login/API-health captures remain the latest evidence.
- No database schema, migration, or stored data changed. The route map and Day43–60 tracker now record Day43 as verified, Days44–47 as in progress pending authenticated native evidence, and Day49 as verified.

Next: manually confirm the emulator seed credential and capture authenticated mobile dashboard/QR/classes/profile screens, then run the isolated database/performance/rebuild gates before the final local archive/tag.
