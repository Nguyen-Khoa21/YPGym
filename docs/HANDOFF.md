# YPGym Handoff

Last updated: 2026-09-16, Day60 local release commit/tag complete.

## September 16 development continuation — current checkpoint

- Read both handoffs and the active attachment brief. Authoritative starting state was `main`/`origin/main` at `fde7f1e`, the September 14 analytics/security/Expo web commit already pushed on explicit user request. Only generated `tmp/` was untracked at entry. The older `bcec6b9`/uncommitted claims below are historical. September 16 release work is recorded in local commit `5161bcc` with annotated tag `v0.60.0`; it was not pushed and normal-volume data was not reset.
- Completed the missing Day53 real-storage CSV/configuration checks in `backend/app/tests/integration/test_configuration_exports.py`: exact filters, empty exports, admin-only permissions, formula escaping, export audits, configuration bounds/type validation, unknown keys, Redis TTL/invalidation and persisted before/after audit.
- Completed Day58 synthetic data in the existing `backend/app/db/seed.py` with opt-in `--demo`; it refuses normal/production storage. `compose.demo.yml` is standalone, uses a separate project/database/storage, no fixed container names and no published DB/Redis ports. Full fixture: 12 users, five roles, three member tiers, all five requested membership states, VND billing/invoice, trainer, three future classes, two bookings, one waitlist, notifications/preferences, broadcast and 22 closed history sessions. Default development seed behavior is preserved; synthetic relative dates and original invoice snapshots are tested.
- The standalone test stack's latest run exited successfully: **102 passed, 5 existing Starlette 422 deprecation warnings in 90.58s**. Test storage stopped normally. Dedicated fixture tests cover repeat runs, 400-day date refresh, counts/IDs, invoice immutability, actual logins, restricted QR, preserved promotion decisions and PT-owned workspace/role boundaries. CORS extra origin is explicit in the test configuration.
- `backend/scripts/demo_smoke.py` passed through actual HTTP on the demo API: purchase/renewal/replay, invoice PDFs, QR/check-in/duplicate/check-out/occupancy, booking/waitlist/promotion, CRM revocation/audit, billing exports and manager-cache/staff/PT denials. Run as a module: `python -m scripts.demo_smoke --base-url http://localhost:8000/api/v1` inside the demo backend. The ordinary backend refused this script's mutations before requests. Smoke intentionally changes synthetic demo records; use the documented demo-only reset to replay from initial fixtures.
- Normal stack is still running at web/API `5174/8001` and DB/Redis `5433/6380`. `ypgym-demo` is retained at web/API `55174/58001` with healthy DB/Redis/API, worker/beat/web up, clean Alembic `20260723_0007` metadata and worker ping/pong. Initial images rebuilt successfully. Never combine the standalone files with the application Compose file or delete normal volumes.
- `docs/demo/demo-script.md` now documents exact commands, credentials, initial states, preconditions/outcomes, all ten examiner steps, private Maildir and isolated reset. `docs/release/uat-checklist.md` has an explicitly adapted SUS-style questionnaire, scoring rules and empty results. No research/UAT participants, responses, scores, proposal FR source or supervisor approval are fabricated. `mobile/README.md`'s Expo web copy command now actually selects localhost instead of copying the emulator URL unchanged.
- Frontend compatible dependency patches completed: manifest unchanged, lockfile updated, Dockerfile uses `npm ci`. Fresh host `npm ci` (session `97301`, exit 0) and physical package-file checks confirm Vite 7.3.6, React Router 7.18.4 and PostCSS 8.5.28. Fresh lint/build/audit (session `63453`, exit 0) pass; zero audit vulnerabilities, known TanStack warning and 739.62 kB bundle warning. The earlier metadata-only update still loaded old physical Vite; only the fresh installation/build count as patched host evidence. Demo frontend rebuild (session `34563`, exit 0) independently installs Vite 7.3.6 and reports audit 0. Official advisories and limitations are linked in `docs/policies/security.md`.
- Installed AVD `Medium_Phone_API_36.1` was launched hidden (launcher PID `27896`); ADB sees `emulator-5554`, Expo Go 57.0.9. Computer-use `sky` now exposes the emulator window `787896`; its process app identity is `C:\Users\Admin\AppData\Local\Android\Sdk\emulator\qemu\windows-x86_64\qemu-system-x86_64.exe`. Bluetooth crash dialog was dismissed; Expo showed `Failed to download remote update`. Metro localhost bound only IPv6 and refused IPv4, so only this task's identified Metro process was stopped and restarted with `npx expo start --go --lan --port 8082`. Do not restart again merely because observation times out: poll the live handle or inspect the listener/process.
- Native launch/download is resolved: LAN Metro responds over IPv4, Expo Go downloaded the 1,854-module Android development bundle, and the actual seeded member login succeeded. Dashboard shows Maya Member's renewed VIP coverage (350 days remaining), 0% occupancy and the persisted broadcast. QR, joined/full/waitlisted class states, Today empty filtering, My Bookings, native cancellation and successful rebooking are captured in `docs/design/evidence/day-47-mobile/*-september16.png`. Profile, renewal selection/success and complete session cases still require capture.
- Native offline/background QA found a real QR recovery defect: failed foreground refresh hid access correctly, but a successful manual retry never restored `foregroundReady`. `mobile/src/app/(member)/(tabs)/qr.tsx` now reuses one refresh callback for foreground return, pull refresh and both retry actions; success restores readiness only while the app is active. Before-fix/offline/recovered captures exist. Repeat the exact offline/background/retry sequence after Fast Refresh before treating the recovery regression as fully verified. Mobile typecheck/lint/two QR policy tests/Android export passed (session `56663`, exit 0); those unit tests do not independently prove callback wiring.
- For native QA ignored `mobile/.env` remains localhost API `8001`; task ADB reverse maps device `8001` to host demo `58001` and device `8082` to host Metro `8082`. Remove only these mappings after verification. `sky` screenshot capture became unreliable despite a live returned emulator window; native ADB screencap/pull provides unobscured Android evidence without touching other user windows. The emulator remains live; do not restart it merely on observation timeouts.
- Day54 query/pagination review passed on fresh temporary storage (session `34596`, exit 0), then only test services were stopped. Existing CRM/attendance queries remain 3 SELECTs at page sizes 20/100; pages are bounded/disjoint. Member class cards use 1 SELECT for 100 classes. Sanitized actual query plans are `docs/release/query-review-september16.json`, with timings/empty billing/audit limitations and index rationale in the performance report. No new migration/index is justified by this dataset.
- Live demo CORS preflights accepted its web origin and Expo localhost8081, denied an unknown origin with 400/no allow-origin. Installed Uvicorn trusts forwarded headers only from 127.0.0.1; a negative probe over the published demo port found forged forwarded addresses did not receive independent limiter keys. No external proxy/deployment path is claimed. Tracked-file path inventory includes only environment examples, no real environment/key/storage/dependency files; full content/archive inventory remains open.
- Further native QA completed Profile → Membership Plan → select 1 Month → explicit simulated-payment confirmation → server-backed Renewal Success: 720,000 VND, expiry October 1, 2027, invoice `YPG-20260916-19851CAD`. Screenshot `renew-success-september16.png` is authentic. Only synthetic demo billing changed. Profile's left badge and renewal's clipped mixed-size day label were observed against BRD Figures20/24 and fixed using the existing Pill and baseline row. Final mobile checks/export passed (session `80069`, exit 0). Capture final polished Profile/selection, invoice details and exact session/recovery cases next. The new native README/route map names all six BRD reference IDs and exceptions without claiming pixel identity.

### Live handles and next exact actions

September16 latest checkpoint (15:31 local): final Profile/renewal-selection/QR captures are saved. Exact final-code background → offline → foreground → Try again sequence passed, with a fresh QR/countdown after restoration. QR clock initializes with `Date.now`, so cached expiry is enforced on mount. Updated mobile typecheck/lint/two QR tests/Android export completed successfully. SecureStore restoration, confirmed logout plus restart, real one-minute expiry401 plus restart, and staff-role denial all passed. Expiry used an extra demo-only API on loopback58002; only its owned container was stopped and the device mapping restored to58001. The latest isolated backend run is 102 passed; frontend lint/build passed with known warnings.

Final web review found Home's stale Day40 label and PT's old planned module screen. Home copy is corrected; lightweight PT workspace now reads the authenticated trainer's existing profile/next-three assignments through `/trainers/me`, reusing `TrainerService`, `ClassRepository`, `TrainerItem` and `PTCard`. No client/earnings workflows are fabricated. New persisted ownership/role/empty/inactive/schedule-filter regression is `test_trainer_workspace.py`. Demo API is loopback-bound in the configuration, and re-seeding cannot shorten the main member's paid renewal coverage; the existing real-purchase seed regression was extended. The dedicated final-source suite completed at 102 passed and frontend lint/build passed with known warnings. Rebuilt demo final-source checks passed; a later full smoke replay correctly stopped at HTTP 409 because the same synthetic class had already been booked. Native billing records remain synthetic and main expiry is preserved by the new seed rule.

The BRD's Section7 contains the unchanged FR1–FR39 identifiers and descriptions. Use those inspected identifiers for source-labelled traceability; do not claim the separately named unavailable proposal was read. The BRD also explicitly allows limited PT schedule management/lightweight dashboard. Traceability, research, architecture and rehearsal notes now carry the current evidence labels. The reviewed archive, local commit and annotated tag are complete; no remote push was made.

1. Metro LAN session `93600` remains live and serving Expo Go. Resume this same handle; a timeout is not terminal. Dependency update `38837`, host install `97301`, patched frontend checks `63453`, query review `34596` and mobile checks/export `56663` completed with exit 0. Earlier localhost Metro `37458` was deliberately stopped after verified IPv4 refusal.
2. Rebuild the loopback demo API/frontend after any further source changes, then run the small PT endpoint and connected smoke checks against that rebuilt image. Keep evidence tied to the isolated demo state.
3. Reconcile any future diagram labels and keep release archives filtered to exclude `tmp/`, secrets, caches and generated dependency/build folders.
4. Day60 is complete locally: archive `C:\Users\Admin\ypgym-day60-20260916.zip`, commit `5161bcc`, annotated tag `v0.60.0`. Do not push remotely unless explicitly requested.

## September 14 session closeout — mobile, release verification, and handoff

- Mobile work is implemented under `mobile/src/app/`, `mobile/src/lib/`, and `mobile/src/components/`: Expo Router member navigation, SecureStore session persistence, member-role guards, dashboard, rotating QR, classes/booking/waitlist, My Bookings, attendance, notifications/preferences, profile editing, invoices, and simulated renewal. `mobile/README.md` contains Android emulator, physical-phone, and Expo web instructions.
- Expo web networking was fixed at the end of the session. The local ignored `mobile/.env` uses `http://localhost:8001/api/v1`; Android emulators use `10.0.2.2`; physical phones use the computer LAN address. `backend/app/main.py` now accepts explicit local Expo origins through `CORS_EXTRA_ORIGINS`, while unknown origins remain denied. Focused CORS tests pass 2/2.
- Fresh mobile checks passed: `npm run typecheck`, `npm run lint`, `npm test` (2 QR safety tests), and `npx expo export --platform android`. The prior Expo Doctor check passed 21/21. Native authenticated dashboard/QR/classes/profile screenshots are still unavailable because no emulator app was available to the computer-use surface.
- Backend functionality added or hardened today includes real manager analytics, UTC-safe/unique analytics aggregates, atomic Redis Lua rate limits with IP guards and `Retry-After`, access-token purpose separation from QR tokens, revoked-membership renewal denial, error/validation/request-log privacy, and ignored development Maildir handling for one-time verification/reset links.
- Isolated verification uses `compose.test.yml`: temporary PostgreSQL/Redis, no host ports, read-only source mount, and guarded cleanup. The latest isolated run passed 94 tests with 4 deprecation warnings; focused CORS checks added 2 more passing tests. The normal development suite passed 64 tests and skipped 27 intentionally outside the isolated environment. No normal development volumes or stored records were reset.
- Day54 benchmark stored 1,000 users, 1,000 memberships, 100 classes, 2,000 bookings, 1,000 attendance sessions, and 1,000 check-in events. Crowdedness and class-list waves returned 1,000/1,000 HTTP 200s; login returned 60 HTTP 200 and 940 intentional HTTP 429 results under the IP limit. This remains a bounded local measurement, not a production capacity claim.
- Alembic remains at `20260723_0007 (head)` with no drift. Frontend lint/build pass with the known TanStack compiler and bundle-size warnings. The last pushed commit is `bcec6b9`; all current release work is uncommitted.
- Suggested commit title for this session: `feat: add analytics security hardening and Expo web connectivity`. Do not include the commit title in a release claim until the remaining native/release gates are reviewed.

## September 14 resume update — isolated verification and security fixes

- The last pushed commit remains `bcec6b9` on `main` and `origin/main`. Current release work is uncommitted; preserve all modified and untracked files. No normal application database, Redis volume, invoice directory, or Celery schedule was reset.
- Added a standalone `compose.test.yml` stack with temporary PostgreSQL/Redis and a read-only backend mount. The final isolated run migrated through `20260723_0007` and passed **94 tests with 4 Starlette deprecation warnings**. The ordinary development suite is **64 passed, 27 skipped** because integration fixtures intentionally skip outside `ENVIRONMENT=test`. Coverage is recorded in `docs/release/integration-report.md`.
- Real-storage coverage now proves registration/verification/reset, five persisted roles and ownership, JWT/access-token versus QR purpose separation, Redis rate-limit races/expiry/outage, scanner limits, QR rotation/expiry, check-in/out races, timeout idempotency, UTC analytics, booking/waitlist races, billing/invoice ownership, freeze/cancellation/revocation decisions and audit records.
- The revoked-membership renewal bypass was fixed in `backend/app/services/membership_service.py` and `membership_repository.py`; terminal revoked memberships can no longer be renewed through self-service.
- `backend/scripts/registered_load.py` created and measured an isolated dataset of 1,000 users, 1,000 memberships, 100 classes, 2,000 bookings, and 1,000 attendance sessions. Crowdedness and class-list waves returned 1,000/1,000 HTTP 200s with no transport errors. Login returned 60/200 and 940/429 because the documented IP rate limit remained enabled. Full conditions/results are in `docs/release/performance-report.md`; this is a bounded local result, not a production-capacity claim.
- Sensitive-link handling now writes development verification/reset messages to an ignored Maildir (`DEVELOPMENT_MAIL_DIR`) instead of logs. JWT access tokens carry `type=access`; QR tokens sharing the signing key are rejected by account authentication. Error/request logging and validation responses no longer expose exception values, query tokens, credentials, or rejected input. Metrics documentation now states UTC bounds, cohort semantics, inclusivity, cache freshness, and VND payment meaning.
- Frontend `npm run lint` passes with the existing TanStack compiler warning; `npm run build` passes with the existing large-bundle warning. `alembic current` is `20260723_0007 (head)` and `alembic check` reports no operations.
- Expo web connectivity was corrected: `mobile/.env` now uses `http://localhost:8001/api/v1`, while physical phones must use the computer LAN address and Android emulators must use `10.0.2.2`. Backend CORS now accepts explicit local Expo web origins on ports 8081, 8082, and 19006 (localhost and loopback); unknown origins remain denied. `backend/app/tests/test_cors.py` passes 2 tests. Restart Metro after changing `.env`.

### Current exact checkpoint

1. Native authenticated evidence is still open: use the normal API (`8001`) and seeded member account to capture dashboard, rotating QR, classes, and profile in the Android emulator. The computer-use inventory previously had no emulator app, so no native authenticated claim is made.
2. Finish Day53 configuration/export checks, Day54 query-plan/index review, Day55 final proxy/CORS and secret inventory review, Day56 rendered accessibility/offline/error review, Day58 full seed/examiner sequence, and Day59 native/shared-backend rehearsal.
3. Only after those gates pass, review the archive, create the authorized local release commit and annotated tag. Do not push remotely. Keep proposal FR1–FR39, UAT, interviews, survey, sources, competitors, and FR39 chatbot variance explicitly unavailable/deferred unless supplied.

## September 14 resume update — Day 49 analytics

- The last pushed commit is `bcec6b9` on `main` and `origin/main` after the user's explicit push request. This analytics batch is currently uncommitted; the untracked temporary `tmp/` extraction directory is also present.
- Manager/admin analytics now has a real `/api/v1/admin/analytics/summary` endpoint. The established repository/service/API layers aggregate persisted membership statuses, class bookings/utilization, attendance check-ins/unique members/visit duration, and successful payment totals for a bounded 366-day range.
- The summary uses a 60-second Redis cache keyed by the normalized date range and exposes `generated_at`, `cache_hit`, and `cache_ttl_seconds`. A live manager request returned persisted data; a repeat request returned `cache_hit=true`; a staff token returned HTTP 403.
- The attendance operations page renders the summary beside the existing 168-cell peak-hours heatmap. The route-screen map now records the endpoint, fields, cache freshness, and native mobile evidence status.
- Validation for this batch: Docker backend suite `62 passed`; `alembic check` reports no new upgrade operations; frontend `npm run build` passes; backend compileall passes. No models, migrations, constraints, or stored records changed.
- The next security slice adds Redis fixed-window limits before login (10/minute per hashed IP+email scope), forgot-password (5/15 minutes per hashed IP+email scope), and scanner check-in/out (60/minute per hashed device scope). It fails closed on Redis errors. Unit coverage now totals 62 passing tests; live login returned ten `401`s then `429`, forgot-password five `200`s then `429`, and scanner `401` then `429` on request 61.
- Day50/57/58 release artifacts now exist: `docs/release/feature-freeze.md`, `bug-list.md`, `requirements-traceability.md`, `uat-checklist.md`, `research-evidence-inventory.md`, `viva-notes.md`, `docs/policies/security.md`, and `docs/demo/demo-script.md`. They intentionally mark unavailable proposal/UAT/research evidence as unavailable.
- A repeatable Day54 probe is now `backend/scripts/load_smoke.py`, documented in `docs/release/performance-report.md`. The development-stack run measured 1,000 synthetic login requests plus 100-request authenticated crowdedness/class-list probes at concurrency 10; it recorded median/p95/max values and one login transport error rather than hiding it. This is a baseline, not a capacity claim, until repeated on a disposable stack.
- Day59 disposable rehearsal passed with a separate Compose project and ports: images rebuilt, empty PostgreSQL migrated through `20260723_0007`, seed applied, API/web health, manager analytics cache, and member dashboard checks passed. The temporary volumes/network were removed and the normal stack remained running. Expo was not pointed at that temporary port, so native/shared-backend rehearsal remains open.
- The September 14 computer-use inventory exposed no native emulator app (`apps: []`), so no authenticated Android screenshot claim was added. The existing launch/login/API-health captures remain the latest native evidence.

### Exact resume checkpoint

1. Confirm the seeded member credential manually in the running Android emulator and capture authenticated dashboard, rotating QR, classes, and profile evidence; current native evidence only proves branded launch/login/API health.
2. Continue Days 50–60: dedicated database/performance/QA checks, isolated rebuild rehearsal, and a reviewed local archive/tag. Keep research/UAT outputs explicitly labelled as unavailable unless supplied.

## September 13 resume update

- The Day 42 interactive responsive gate is now verified. The real-browser evidence index is `docs/design/evidence/day-42/README.md`; the four routes were checked at desktop, tablet, and phone widths with interactions and loading/empty/error/role states. The latest 1440/768/390 checks found no document-width overflow. This clears the Day 43 start condition, while BRD pixel parity remains a separate Day 46/47 check.
- Fresh backend health and all 59 backend tests passed. The frontend lint/build are being rerun for the accumulated responsive fixes. No user-owned changes, volumes, or existing QA records were discarded.
- The user asked to finish mobile UI and functions, then give Windows run instructions. `mobile/` did not exist at entry. The Day 43 Expo scaffold is being created; completion and native launch are not yet claimed.
- `docs/progress/day-43-60-tracker.md` records milestone status. This update supersedes the stale September 7 baseline lines below.

## Active continuation — 2026-09-07

- User authorized continued implementation through Day 60, preserving the Day 42 interactive responsive gate before Day 43. Scope/evidence tracker: `docs/progress/day-43-60-tracker.md`.
- Actual starting HEAD is `69dcb8b` on `main`; the July starting-commit statements below are historical. No new commit/tag has been created. The final local release commit/tag is authorized only after required verification; no remote push/public deployment is authorized.
- Pre-existing modified/deleted/untracked files are inventoried in the tracker and remain untouched. New work so far: tracker and original BRD images extracted into `docs/design/references/`; temporary text extraction is `tmp/brd-extracted.txt`.
- Frontend baseline `npm run lint` passes with the known TanStack warning; `npm run build` passes with the known 730.67 kB bundle warning. `docker compose config --quiet` passes. Docker Desktop was stopped, then launched hidden; the first build attempt failed during daemon startup. Server `29.4.3` subsequently responded and the second Compose build is running. Existing volumes and old containers are preserved.
- Browser tooling now discovers the in-app browser, including viewport and screenshots. No rendered checkpoint is yet claimed. The full local revised plan and historical/current handoffs were read; the named proposal was not found in the repository and its path has been requested. FR identifiers must not be fabricated.
- Next: finish Compose build; run backend tests, Alembic current/check and live VND/invoice checks; complete the four-route Day 42 desktop/tablet/phone checkpoint with screenshots and observed-defect fixes. Start Day 43 only after the checkpoint passes.

The remaining sections preserve the July baseline until fresh evidence supersedes each claim.

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
