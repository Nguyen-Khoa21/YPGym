# Isolated integration evidence

## September 16 continuation

The earlier storage run covered 101 tests. The latest final-source run executed `docker compose -p ypgym-tests -f compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner --attach test-runner`: migrations applied to the dedicated temporary database, **102 passed, 5 warnings in 90.58 seconds**. The five warnings are the existing Starlette 422 deprecation. The test stack stopped normally with exit code 0; normal application services remained running.

New real-storage coverage: configuration role denial, integer/range validation, unknown keys, cache TTL/invalidation and atomic persisted audit; admin-only CRM/payment/invoice CSV exports with matching filters, empty results, spreadsheet-formula escaping and export audits; full synthetic seed count/ID repeatability, all membership states/member tiers, 400-day relative-date refresh, immutable invoice snapshots, real account login/QR restrictions and booking/waitlist promotion preserved on re-seed. `compose.test.yml` now explicitly provides the Expo CORS origin the test exercises.

The separate demo stack also passed the connected HTTP journey through `python -m scripts.demo_smoke --base-url http://localhost:8000/api/v1`. It used actual HTTP and JWT endpoints, invoice PDFs, QR/device scans, checkout/occupancy, booking/promotion, CRM/audit, exports, manager cache and role denials. Its guard refused ordinary development storage before requests. Native/browser rendering, performance review and human research/UAT remain separate gates.

The sections below preserve earlier measurements, not the current test count.

Run on 2026-09-14 with `compose.test.yml`, using a separate network, temporary PostgreSQL data, temporary Redis, no host ports, and a read-only backend source mount. Fixtures refuse to truncate any database except `test-postgres/ypgym_test`.

## Commands and outcomes

```powershell
docker compose -p ypgym-tests -f compose.test.yml up --abort-on-container-exit --exit-code-from test-runner --attach test-runner
```

The final run applied migrations through `20260723_0007` and completed **94 passed, 4 warnings** in 25.05 seconds. Warnings are Starlette's deprecation notice for `HTTP_422_UNPROCESSABLE_ENTITY`. The ordinary development suite reports **64 passed, 27 skipped** because integration tests intentionally skip outside `ENVIRONMENT=test`.

Coverage includes persisted registration/verification/reset, all five roles and ownership, JWT/QR purpose separation, Redis counter races/expiry/outage, scanner/device limits, QR rotation and expiry, check-in/out races, timeout idempotency, occupancy/UTC analytics, class capacity/waitlist promotion, billing/invoice ownership, freeze/cancel/revoke decisions, audit records, terminal revocation purchase denial, and validation/error/mail privacy. See the integration test files under `backend/app/tests/integration/` for the executable cases.

This does not replace authenticated Android rendering, final route-level accessibility review, the full CSV/export security pass, proxy-aware client-IP deployment configuration, or human UAT/research. Those remain tracked separately.
