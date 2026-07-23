# YPGym Handoff

Last updated: 2026-07-23, after role-aware Workspace navigation.

## Current milestone

- Branch: `main`; starting commit: `de64c1e` (`feat: complete YPGym operations workflows through Day 38`). No commit, reset, clean, stash, push, or history rewrite was performed.
- The initial user-owned modified revised-plan file and untracked `AGENTS.md`/Day 22-38 prompt were preserved. Backup: `C:\Users\Admin\.codex\backups\ypgym-20260722-132422`.
- Days 37-38 passed the prerequisite gate without repair. Days 39-41 are complete and Day 42 is connected and code-verified across service/API/RBAC and React, but final acceptance remains partial for the responsive browser checkpoint below.
- Database is at the single Alembic head `20260723_0007`; metadata drift check is clean.

## Implemented Days 39-42

- Day 39: nullable trainer bio/availability profile fields, active public cards with batched upcoming-class summaries, audited manager/admin create/update/deactivate, and a deactivation guard that requires future class reassignment.
- Day 40: membership-aware upcoming class payload, trainer/capacity/member-state cards, member booking, duplicate/full/started/cancelled checks, and class-row locking that prevents concurrent overbooking.
- Day 41: configured inclusive cancellation cutoff, member ownership, My Bookings UI, waitlist join/leave and deterministic order, atomic earliest-eligible promotion, ineligible-entry skipping, and preference-aware deduplicated promotion notifications.
- Day 42: one typed `/dashboard/me` payload for current membership/QR eligibility, crowdedness, bounded bookings/waitlists, unread count and the three most recent unread in-app notifications, active broadcasts, and quick actions; the responsive dashboard uses only this real payload.

## VND billing localization

- Migration `20260723_0007` converts the six seeded plan prices and existing local mock payment/invoice amounts from the former RM-scale values using a fixed 6,000 multiplier. The downgrade reverses the conversion.
- New and existing seed data uses VND-scale values; the one-month plan is 720,000 VND and the three-year plan is 16,200,000 VND before its configured discount.
- The shared React formatter uses `vi-VN`/`VND` with no fractional digits. Regenerated invoice PDFs use grouped ASCII `VND` amounts.
- Invoice PDFs are regenerated from immutable invoice metadata when downloaded so pre-migration files cannot retain stale RM labels.
- Pre-migration database backup: `C:\Users\Admin\.codex\backups\ypgym-vnd-20260723\ypgym-before-vnd.dump`; SHA-256 `035F43388648DD76404076942CAAA1E374904D90BD53E6E2A53CF211E5BC2C74`.

## Today's update — 2026-07-23: role-aware Workspace navigation

- Member logins still resume their originally requested protected member route.
- Admin, manager, and staff logins always enter `/admin`; personal trainers always enter `/pt/dashboard`. A stale member-route redirect can no longer send these roles through `/permission-denied` immediately after successful authentication.
- Every signed-in `AppFrame` now includes a visible Workspace button using the same typed role mapping, so members, operations roles, and personal trainers can return to their dashboard from any shared page.
- The permission-denied screen now uses the shared role mapping for its return link; frontend/backend role guards remain unchanged for genuine unauthorized navigation.

## Business decisions

- Trainer deactivation is blocked while any scheduled future class remains assigned.
- Booking, waitlist position allocation, cancellation, and promotion serialize on the class row with PostgreSQL `FOR UPDATE`.
- Cancellation is allowed at the exact configured cutoff and rejected immediately after it.
- Waitlist order is stored position, creation timestamp, then UUID. Cancellation auto-enrols the first eligible entry; ineligible entries become cancelled and scanning continues.
- Promotion notification records are created only for enabled in-app/email channels and use unique dedupe keys.

## Verification evidence

- Baseline before edits: 43 pytest tests passed; frontend lint had zero errors/one documented TanStack warning; frontend build passed; Alembic current/head `20260716_0005` and drift check clean.
- Focused final backend run: 59 pytest tests pass; compileall passes; Alembic check reports no new operations.
- VND verification: PostgreSQL contains the six expected VND plan prices and 13 converted mock payments/invoices; the public formatter produces `720.000 ₫`; an authenticated invoice download was regenerated and extracted as `VND 5,508,000`, with no RM label.
- Day 39 live flow: manager create/update, assigned-future-class deactivation conflict, reassignment, successful deactivation, member denial, and inactive public filtering passed.
- Day 40 live flow: active/ineligible listing, ineligible denial, booking, duplicate denial, started-class denial, and a simultaneous two-member capacity race returned `200/409` with exactly one confirmed booking.
- Day 41 live flow: positions `1,2`, duplicate/booked-member waitlist denial, revoked first-entry skip, second-entry promotion, notification, ownership denial, idempotent repeat cancellation, late denial, and simultaneous duplicate cancellation with one promotion all passed.
- Day 42 live flow: active, revoked, and no-membership payloads passed; QR/access status, active broadcasts, bounded upcoming bookings, authenticated-user isolation, manager denial, and dashboard deep-link HTTP 200 passed. The final parity check inserted a newer read item and four unread items, then confirmed the read item was excluded, the top three unread items matched PostgreSQL order, and the unread count matched before removing the test records.
- Broad live regression: registration plus duplicate email/phone rejection, email verification, role-aware login, profile update, forgot/reset with one-time token reuse rejection, membership purchase/renewal and idempotency, invoice history/PDF, notifications/broadcasts, rotating QR/device/duplicate-scan enforcement, check-in/out and crowdedness reconciliation, 168-cell peak-hours analytics, CRM/billing CSV exports, and expected 401/403 boundaries passed.
- Idempotent seed verification after two consecutive runs returned exactly six named plans, five named demo users, one seeded payment, invoice, welcome notification, and linked trainer. The attendance-timeout task executed successfully and found zero stale sessions to close.
- Protected web deep links `/app/dashboard`, `/app/classes`, `/app/bookings`, `/app/qr`, `/admin/pt-assignments`, `/admin/classes`, `/admin/members`, and `/admin/attendance` all returned the Vite SPA shell with HTTP 200.
- Frontend lint/build passes after each meaningful UI slice. The final known warning remains the TanStack React Compiler compatibility warning; the main bundle is about 731 kB minified.
- Interactive browser QA could not run because the browser runtime reported no available browsers after the required troubleshooting check. Responsive source states, local route HTTP, TypeScript, Vite transformation, and production build are verified; screenshots are not claimed.

## Exact resume checkpoint

1. Repeat interactive desktop/tablet/mobile QA for `/app/dashboard`, `/app/classes`, `/app/bookings`, and `/admin/pt-assignments` when a browser backend is available. The 2026-07-23 retry again returned an empty browser list. Record screenshots/results in `docs/progress/day-39-42-audit.md`.
2. Only after that check passes, change Day 42 from `partial` to `complete` and consider Day 43.

## Start and verify

```powershell
docker compose --profile app up -d --build
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api python -m app.db.seed
docker compose exec -T backend-api pytest -q

cd frontend
npm run lint
npm run build
```

Open `http://localhost:5174`. Accounts and ports are in the root README. Use `docs/demo/day-39-42-demo.md`; API and policy details are in `docs/api/classes-booking-dashboard.md`.

## Known limitations

- Final interactive desktop/tablet/mobile screenshot QA remains unexecuted because no in-app browser backend was available.
- The main Vite bundle and existing TanStack compiler warning remain pre-existing/non-blocking technical debt.
- Promotion email is the existing development notification-record/log flow, not an SMTP provider.
- Waitlist positions are monotonic stored order values; cancelled/promoted gaps are not renumbered.
- The development database contains disposable verification accounts/classes created by live API checks; no schema or production data was destructively changed.
- The fixed 6,000 conversion is intentional deterministic demo pricing, not a current market FX rate or live conversion service.
- Expo/mobile, personalization/recommendations, AI chatbot expansion, live payment settlement, physical hardware, and advanced PT business management remain Day 43+ or otherwise out of scope.

## Next development boundary

Repeat interactive responsive QA when a browser backend is available. Begin Day 43 only after that checkpoint passes; reuse the existing `/dashboard/me`, class, booking, and trainer contracts rather than creating a separate mobile backend.
