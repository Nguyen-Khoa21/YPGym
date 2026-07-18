# YPGym Handoff

Last updated: 2026-07-18, after crash recovery and Days 21-38 completion.

## Current milestone

- Git branch remains `main` at the pre-existing commit `a91573b`; no commit, reset, clean, stash, or push was performed.
- The uncommitted interrupted tree was preserved and extended in place.
- External recovery copy: `C:\Users\Admin\ypgym-recovery-20260718-141935` (211 eligible files, SHA-256 verified with zero mismatches).
- Pre-migration PostgreSQL dump: `ypgym-pre-day22-38-recovery.dump` in that backup, SHA-256 `520EF9ED83A3B567652EB698E27A587917E8B7993E2F32D07A854656E9D8CD72`.
- Database is at the single Alembic head `20260716_0005`; metadata drift check is clean.

## Completed scope

Days 21-38 are connected across backend, PostgreSQL/Redis/Celery, React routes, RBAC, seed/demo records, simulator contract, and documentation. Important integration repairs made during recovery:

- explicit membership/user relationship foreign keys after adding `revoked_by_id`;
- valid `.dev` seeded identities, with idempotent migration of existing `.local` rows;
- effective-state cancellation eligibility rather than trusting stale stored state;
- member QR/history, attendance operations/analytics, admin classes, notifications, CRM, billing, audit, configuration, broadcasts, and manager approval queue routes;
- exact-filter CRM/billing CSVs and audit entries;
- idempotent representative payment/invoice/notification/attendance/class/device seeds;
- scanner invalid/expired/superseded/inactive/duplicate/unauthorized paths and documented contract.
- per-task async-engine disposal so sequential Celery jobs never reuse asyncpg connections from a closed event loop.

## Verification evidence

- Backend: 43 pytest tests pass; compileall passes; lifecycle, reminder, and timeout workers pass sequential execution in one process.
- Database: `alembic current` at `20260716_0005`; `alembic check` reports no new operations.
- Live API: 23 scanner/attendance checks and 42 operations/RBAC checks pass; manager approval queue/staff denial, revoked-access denial, and class-overlap rejection pass separately.
- Legacy regression: 24 live checks pass for registration uniqueness, verification, login/auth resolution, profile/password updates, forgot/reset one-time token behavior, six plans, purchase, renewal, idempotency, billing histories, PDF download, and member admin denial.
- Frontend: ESLint has zero errors (one documented TanStack/React Compiler compatibility warning); TypeScript/Vite production build passes.
- Protected-route deep links `/app/qr`, `/admin/members`, `/admin/approvals`, and `/admin/classes` return the SPA shell over HTTP; interactive auth refresh remains part of the unavailable browser pass.
- Live services: PostgreSQL and Redis healthy; API health succeeds; frontend root and transformed route/QR/approval modules return HTTP 200 after container dependency synchronization.
- Seed: two consecutive runs retain exactly one seeded payment, invoice, and notification plus five demo identities.
- Visual limitation: the in-app browser backend was unavailable (empty browser list), so no final interactive screenshot pass was possible. Source references, responsive CSS, live module transforms, and production build were verified.

## Start and verify

```powershell
docker compose --profile app up -d
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api python -m app.db.seed
docker compose exec -T backend-api pytest -q

cd frontend
npm install
npm run lint
npm run build
```

Accounts and routes are in the root README. The complete demo is `docs/demo/day-21-38-demo.md`; scanner details are `docs/api/iot-scanner.md`.

## Known non-blocking risks

- The main Vite bundle is about 713 kB minified; route-level lazy loading is deferred technical debt.
- React Compiler skips optimization for the TanStack Table hook and emits one lint warning; behavior/build are unaffected.
- `npm audit` reports four development-tool advisories (two low, one moderate, one high), while `npm audit --omit=dev` reports zero production dependency vulnerabilities; upgrade Vite/Babel tooling deliberately rather than applying an unreviewed forced update.
- The development Celery worker runs as root inside its container and emits the standard warning; configure a non-root image user before production deployment.
- The manager approval repository combines two request query sets before application-level pagination. It is correct for current volume; a SQL union/window query is the scaling improvement.
- Visual browser QA should be repeated when the in-app browser is available.

## Next development boundary

Resume at Day 39: PT profile management and member-facing PT cards. Do not fold Day 40 member class booking/waitlist behavior into Day 39. Preserve the audited lifecycle, role matrix, configuration, and attendance source-of-truth rules documented here.
