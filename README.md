# YPGym

YPGym is a PostgreSQL/FastAPI/React gym-operations application. The connected web scope covers authentication and billing, membership lifecycle decisions, CRM, notifications, audited exports, system configuration, rotating QR attendance, occupancy and manager analytics, trainer profiles, transaction-safe class booking/waitlists, and an integrated member dashboard. The Day 43–47 Expo member app uses the same backend contracts; its documented Android emulator rehearsal covers the member journeys and session/error states listed in `docs/design/evidence/day-47-mobile/README.md`.

The implementation follows `YPGym_60_Day_Development_Plan_Revised_PostgreSQL (1).md`. Detailed recovery evidence is in `docs/recovery/day-22-38-recovery-audit.md`; the current continuation contract is in `docs/HANDOFF.md`.

## Stack

- React 19, Vite, TypeScript, Tailwind CSS, TanStack Query/Table, React Hook Form, Zod
- FastAPI, SQLAlchemy async, Alembic, PostgreSQL 16
- Redis for rotating QR state, occupancy/configuration/analytics caches, sensitive-endpoint rate limits, and Celery transport
- Celery worker/beat for membership status, expiry reminder, and attendance-timeout jobs
- Optional hardware-agnostic IoT scanner simulator
- Expo/React Native member app in `mobile/` (see `mobile/README.md` for Android emulator and phone setup)

## Connected routes

Member routes:

- `/app/dashboard`, `/app/profile`, `/app/billing`
- `/app/qr`, `/app/attendance`
- `/app/membership-requests`
- `/app/notifications`, `/app/notifications/preferences`
- `/app/classes`, `/app/bookings` for live capacity, trainer cards, booking, cancellation, waitlist, and promotion states.

Operations routes:

- `/admin` for staff/manager/admin role-specific navigation
- `/admin/attendance` for staff, manager, and admin
- Manager/admin attendance view includes peak-hours heatmap and persisted membership/class/attendance/revenue summary analytics.
- `/admin/approvals`, `/admin/broadcasts`, `/admin/audit`, `/admin/settings` for manager/admin
- `/admin/members`, `/admin/members/:id`, `/admin/billing`, `/admin/classes` for admin
- `/admin/pt-assignments` for manager/admin trainer profile maintenance.

The current feature set also includes the native member dashboard, rotating QR recovery, classes and booking/waitlist flows, renewal and invoice history, SecureStore session recovery, and a connected personal-trainer workspace. Release hardening covers isolated demo data, audited exports, bounded query review, role/ownership tests, and privacy-safe session/error handling.

## Run locally

Copy environment examples if local overrides are needed, then start the existing volumes and services:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
docker compose --profile app up -d --build
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api python -m app.db.seed
```

The seed is idempotent. It creates six membership plans, six operational configuration keys, one device, representative billing/invoice/notification/attendance/class/trainer records, rolls the seeded scheduled demo class forward when it has passed, and creates these accounts (password `YPGymDemo123!`):

| Role | Email |
|---|---|
| Admin | `admin@ypgym.dev` |
| Manager | `manager@ypgym.dev` |
| Staff | `staff@ypgym.dev` |
| Personal trainer | `pt@ypgym.dev` |
| Member | `member@ypgym.dev` |

`.local` demo identities from the interrupted workspace are migrated to the same `.dev` identities without replacing their IDs or history.

## Ports

- Web: `http://localhost:5174`
- API: `http://localhost:8001`
- OpenAPI: `http://localhost:8001/docs`
- Health: `http://localhost:8001/api/v1/health`
- PostgreSQL: `127.0.0.1:5433`
- Redis: `127.0.0.1:6380`

## Verification

```powershell
docker compose config
docker compose exec -T backend-api alembic current
docker compose exec -T backend-api alembic check
docker compose exec -T backend-api pytest -q

cd frontend
npm run lint
npm run build
```

The September 16 isolated run reports 102 passing backend tests with five Starlette deprecation warnings, including real PostgreSQL/Redis integration, repeatable demo scenarios and CSV/configuration checks. Alembic remains at `20260723_0007`. Native/rendered release gates are separately tracked in `docs/progress/day-43-60-tracker.md`. The implementation and `v0.60.0` tag were pushed on the user's September 16 request; that does not publish the local ZIP.

The September 17 review reconciles the FR1–FR39 platform matrix, API/PT/schema documentation and editable diagrams, and replaces the old archive because it included generated invoices. Use `docs/release/archive-inventory.md` for the sanitized package and integrity inventory. The packager uses the standard library and Git's source inventory:

```powershell
python -m unittest discover -s scripts -p 'test_*.py' -v
python scripts/package_release.py --output C:\Users\Admin\ypgym-release-20260917.zip
```

Choose a new output filename outside the repository on subsequent runs. The ZIP contains reviewed non-ignored working-tree additions as well as tracked files; inspect `git status` before packaging.

Run the real-storage tests from the repository root using their standalone Compose file:

```powershell
docker compose -p ypgym-tests -f compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner --attach test-runner
```

This creates dedicated PostgreSQL/Redis services without host ports, runs migrations and tests, then stops those services. PostgreSQL and invoice output use temporary filesystems. Integration fixtures refuse any database outside this test stack; normal `backend-api pytest` runs skip them. Never combine this file with the application Compose file. See `docs/release/integration-report.md` for coverage and remaining gates.

The standalone `compose.demo.yml` starts a separate examiner stack with automatic migrations/scenario seed, worker/beat and separate storage at web `55174` and API `58001`: `docker compose -p ypgym-demo -f compose.demo.yml up -d --build`. See `docs/demo/demo-script.md` for synthetic states, HTTP rehearsal, interactive tasks and isolated reset commands. The normal seed retains its development behavior; `--demo` refuses normal/production storage. Frontend images now install the npm lockfile with `npm ci`.

In development, registration and password-reset emails are prepared in the ignored `backend/storage/mail/new/` Maildir outbox. Open the newest message with a text editor or mail client and use its one-time link. These private links are no longer printed to application or Uvicorn access logs. `DEVELOPMENT_MAIL_DIR` can relocate the outbox; keep it outside release archives. This local outbox does not deliver external SMTP mail.

Membership plans, mock payments, billing totals, and regenerated invoice PDFs use VND. Migration `20260723_0007` converts the existing development billing records with the fixed project conversion of 6,000 VND per former RM unit; this is deterministic demo pricing, not a live foreign-exchange integration.

The scanner contract and simulator scenarios are documented in `docs/api/iot-scanner.md`. Trainer, booking, waitlist, dashboard, and manager analytics contracts are documented in `docs/api/classes-booking-dashboard.md`; the examiner runbook is `docs/demo/demo-script.md`. The Day54 probe and Day59 disposable rehearsal are documented in `docs/release/performance-report.md` and `docs/release/rehearsal-report.md`. From `iot-simulator/`, run `python -m app.main --help` for all supported scenarios.

## Architecture rules and scope

- Backend layering is API -> service -> repository -> SQLAlchemy model -> PostgreSQL.
- PostgreSQL is the attendance source of truth; Redis state is short-lived or reconcilable.
- Protected UI routes mirror backend role checks, and sensitive mutations/exports create audit records.
- Login, reset-request, and scanner mutations use Redis-backed fixed-window limits; see `docs/policies/security.md`.
- The BRD Design Architecture, `docs/design/route-screen-map.md`, and the shared local design system are the UI authority used for this recovery.
- Days 39-42 preserve the same layering and serialize every class-capacity change on the PostgreSQL class row.
- Real payment-gateway settlement, physical-device firmware, advanced PT workflows, and AI/personalization remain outside the completed scope.
