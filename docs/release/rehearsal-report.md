# Day59 disposable-stack rehearsal

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
