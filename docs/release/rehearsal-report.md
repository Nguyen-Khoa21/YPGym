# Day59 disposable-stack rehearsal

## September 16 repeatable demonstration stack

The reviewed standalone configuration is now `compose.demo.yml`, project `ypgym-demo`. It rebuilt backend, worker/beat and frontend images (frontend uses lockfile installation through `npm ci`), migrated a fresh project database through `20260723_0007`, automatically seeded the complete synthetic scenario set and started all six services. API/dependency health and web HTTP 200 passed; Alembic reports no metadata drift; Celery inspect ping returns pong. Normal application services/volumes remained running on their original ports.

Exact root commands:

```powershell
docker compose -p ypgym-demo -f compose.demo.yml config --quiet
docker compose -p ypgym-demo -f compose.demo.yml up -d --build
docker compose -p ypgym-demo -f compose.demo.yml exec -T backend-api python -m scripts.demo_smoke --base-url http://localhost:8000/api/v1
docker compose -p ypgym-demo -f compose.demo.yml exec -T backend-api alembic check
docker compose -p ypgym-demo -f compose.demo.yml exec -T celery-worker celery -A app.workers.celery_app inspect ping --timeout 5
```

Connected HTTP rehearsal passed purchase/renewal/idempotency, invoice PDFs, current QR/scanner/duplicate/checkout/occupancy, capacity and deterministic waitlist promotion, audited CRM revocation, billing exports and manager-cache/staff/PT denials. Initial smoke attempts exposed invocation and API-client prefix/authentication mistakes in the new script; these were corrected before the complete pass. No domain authorization was weakened. All smoke mutations are synthetic and guarded to the isolated demo database.

Demo endpoints: web `55174`, API `58001`; PostgreSQL/Redis have no host ports. Private invoice/mail output is in a separate demo volume. Full fixture dates/IDs/invoice safety are covered by the isolated suite (latest final-source run: 102 passed). See `docs/demo/demo-script.md` for the interactive sequence and safe demo-only reset.

The initial full HTTP smoke passed from a fresh demo state. A later replay reached the class-booking step with HTTP 409 because the same synthetic class had already been booked by the earlier smoke/native rehearsal; this is the documented mutated-fixture precondition, not an application failure. Final-source checks still passed for demo health, member dashboard expiry, PT self-workspace (without secret fields), and staff denial.

Android AVD `Medium_Phone_API_36.1` was launched with installed tooling; ADB exposes `emulator-5554`, Expo Go 57.0.9. After switching Metro to a LAN binding and reversing only the task-owned API port to loopback58001, the native rehearsal passed member login, dashboard, QR, classes, bookings/cancel/rebook, renewal/invoice, profile, QR offline/retry, SecureStore restore/logout/expiry and member-only role denial. Captures and exceptions are indexed in `docs/design/evidence/day-47-mobile/`. The prior September 14 teardown below refers only to that earlier rehearsal.

Completed 2026-09-14 using Compose project `ypgym-rehearsal`, separate container names, host ports `5543` (PostgreSQL), `5580` (Redis), `58001` (API), and `55174` (web), plus project-scoped disposable volumes.

## Rehearsal checks

1. `docker compose ... config --quiet` passed.
2. `docker compose ... --profile app up -d --build` rebuilt backend, worker/beat, and frontend images and started healthy PostgreSQL/Redis dependencies.
3. `alembic upgrade head` applied the complete migration chain through `20260723_0007` on the empty database.
4. `python -m app.db.seed` created the idempotent development data.
5. API health/dependency checks passed; the web shell returned HTTP 200.
6. Manager login and `/admin/analytics/summary` returned HTTP 200; a repeat returned `cache_hit=true`.
7. Member login and `/dashboard/me` returned Maya Member's live dashboard payload.
8. The disposable project was removed with its own volumes and network. The normal `docker compose ps` stack remained running on ports 5174/8001/5433/6380.

The Expo app was not pointed at the temporary host port during this rehearsal. Native authenticated evidence remains the open Day44/47 item and must be captured against the normal documented API runbook.
