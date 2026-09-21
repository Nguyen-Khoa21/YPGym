# Isolated integration evidence

## September 21–22 post-Day-60 Feature 3

The fresh isolated command `docker compose -p ypgym-yptrain-f3-tests -f compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner --attach test-runner` migrated temporary PostgreSQL storage through `20260921_0008` and completed **105 passed, 5 warnings in 45.05 seconds**. The warnings remain Starlette's `HTTP_422_UNPROCESSABLE_ENTITY` deprecation. The isolated project and volumes were removed afterward; normal application records were not reset.

Feature 3 storage coverage proves preference-aware and deduplicated class reminders, persisted booking action metadata, member inbox ownership, and gym-timezone attendance-day aggregation across a UTC date boundary. Existing integration coverage still exercises registration/verification, membership eligibility, simulated billing/idempotency, invoice ownership, QR expiry/rotation, booking/waitlist conflicts, and session authorization. Mobile typecheck/lint, nine Node tests and Android export pass. Web lint/build pass with their existing warnings. Authenticated Expo web on port 8081 additionally confirmed live API connectivity, login, lifecycle-request history/forms, four distinct visit days and the class-reminder preference. No device-push provider was configured, and physical phone/iOS/human UAT were not exercised.

The normal development stack was forward-migrated to `20260921_0008` and rebuilt. API health passed, Alembic reported the expected single head with no metadata drift, and the minute-scheduled reminder task completed twice with result `0` and no errors against the current development data.

## September 21 post-Day-60 Feature 2

The fresh isolated command `docker compose -p ypgym-yptrain-f2-tests -f compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner --attach test-runner` migrated temporary PostgreSQL storage through `20260723_0007` and completed **102 passed, 5 warnings in 51.80 seconds**. The warnings remain Starlette's `HTTP_422_UNPROCESSABLE_ENTITY` deprecation. The isolated Compose project was removed afterward; normal application volumes and stored data were not touched. Normal `docker compose config --quiet`, `alembic current` and `alembic check` also passed with no pending migration operations.

Feature 2 adds one mobile contrast/token test, bringing the mobile Node suite to seven passing tests. Mobile TypeScript checking, ESLint and Android export pass. Web ESLint and the production build pass with the existing TanStack Compiler and large-bundle warnings. Expo-web review passed at phone, tablet and desktop widths without horizontal overflow. A native Android Expo Go login against the normal API confirmed Dashboard, Check-in, Classes and Profile navigation and server-backed cancelled-membership restrictions through the accessibility tree. The headless emulator framebuffer remained black during capture, so native screenshots are not presented as visual evidence. Physical phone, iOS and human UAT remain separate gates.

## September 20 post-Day-60 Feature 1

The fresh isolated command `docker compose -p ypgym-postday60-tests -f compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner --attach test-runner` migrated a temporary PostgreSQL database through `20260723_0007` and completed **102 passed, 5 warnings in 67.27 seconds**. The warnings remain Starlette's `HTTP_422_UNPROCESSABLE_ENTITY` deprecation. The test project was removed afterward; normal application volumes were not touched.

This run freshly covers failed mock payment, idempotent repeated purchase, active renewal and immutable invoice ownership; approved cancellation/freeze and QR denial; revoked renewal denial; expired JWT rejection; member/role ownership and the broader stored-data regression. Feature 1 also adds six mobile Node tests covering QR safety, logout cache/storage/navigation ordering, member restoration, retryable offline restoration, expired-session discard, active-to-cancelled and active-to-renewed cache refresh, and Back fallback behavior. Mobile typecheck, lint and Android export pass. The Android emulator confirmed cancelled-state messaging/QR denial and logout persistence across an Expo Go force-stop/reopen. Physical phone and iOS were not exercised.

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
