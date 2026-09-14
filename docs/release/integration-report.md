# Isolated integration evidence

Run on 2026-09-14 with `compose.test.yml`, using a separate network, temporary PostgreSQL data, temporary Redis, no host ports, and a read-only backend source mount. Fixtures refuse to truncate any database except `test-postgres/ypgym_test`.

## Commands and outcomes

```powershell
docker compose -p ypgym-tests -f compose.test.yml up --abort-on-container-exit --exit-code-from test-runner --attach test-runner
```

The final run applied migrations through `20260723_0007` and completed **94 passed, 4 warnings** in 25.05 seconds. Warnings are Starlette's deprecation notice for `HTTP_422_UNPROCESSABLE_ENTITY`. The ordinary development suite reports **64 passed, 27 skipped** because integration tests intentionally skip outside `ENVIRONMENT=test`.

Coverage includes persisted registration/verification/reset, all five roles and ownership, JWT/QR purpose separation, Redis counter races/expiry/outage, scanner/device limits, QR rotation and expiry, check-in/out races, timeout idempotency, occupancy/UTC analytics, class capacity/waitlist promotion, billing/invoice ownership, freeze/cancel/revoke decisions, audit records, terminal revocation purchase denial, and validation/error/mail privacy. See the integration test files under `backend/app/tests/integration/` for the executable cases.

This does not replace authenticated Android rendering, final route-level accessibility review, the full CSV/export security pass, proxy-aware client-IP deployment configuration, or human UAT/research. Those remain tracked separately.
