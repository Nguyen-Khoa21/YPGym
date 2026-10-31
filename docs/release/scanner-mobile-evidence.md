# Dedicated attendance scanner release evidence

Date: 2026-10-27 (Asia/Bangkok)

## Audited repository state

- Implementation began from `main` at `4224a2b79a3cbb34dc879105fa670ce2fb1bc188`.
- During final verification, `main` and `origin/main` advanced to `a62a835e661971d1f13d6bd2a31df358a5ff88b7` (`fix(admin): fixed members list`). That commit changes administrator member-list contracts and does not alter the scanner, attendance, realtime, or member mobile paths. The final isolated backend suite and client checks ran against the advanced working tree.
- The working tree contained pre-existing and concurrent changes outside this feature. They were preserved and were not included in scanner work.
- No commit, push, deployment, credential rotation, or external-service change was performed for this feature.

## Implemented scope

- A separate Expo SDK 58 app exists under `scanner-mobile/`. It contains only device provisioning, camera scanning, explicit check-in/check-out selection, and safe result/error displays.
- Existing `/attendance/check-in` and `/attendance/check-out` responses remain backward compatible and now also return the server-derived display name, effective membership status, resulting attendance status, and action.
- Device credentials are verified by the backend and stored in SecureStore. A device key is never configured through `EXPO_PUBLIC_*` or bundled source.
- An authenticated first-frame WebSocket subscription distributes Redis-backed invalidation events. PostgreSQL and authorized REST endpoints remain authoritative.
- Scanner check-in/check-out, timeout, and manual-close transitions publish only after commit. Realtime publication failure does not undo committed attendance.
- The existing web and member mobile apps invalidate and refetch their established TanStack Query data after relevant events, reconnect, and foreground recovery.
- No offline scan queue, scan history, direct database/Redis access, member login, payment, class, training, CRM, or administration feature was added to the scanner app.

## Phase 0 audit record

- Reused: the existing device-authenticated check-in/check-out endpoints, `AttendanceService`, `AttendanceRepository`, attendance models/events, membership lifecycle checks, rotating QR JWT/JTI state, duplicate guard, row locks/partial uniqueness, occupancy reconciliation, error envelope, timeout worker, TanStack Query clients, and the simulator contract.
- Confirmed gaps at the audited baseline: scanner success responses lacked the member-safe identity/status/result fields, no authenticated cross-client attendance invalidation existed, and no dedicated physical-phone scanner application existed.
- Chosen design: additive response fields; first-frame access-token WebSocket authentication; current database user/role lookup; Redis Pub/Sub invalidations after PostgreSQL commit; authoritative REST refetch by clients; a separate reducer-driven Expo app; development-only manual provisioning verified by the backend and stored in SecureStore.
- Dependencies were limited to the new app. Expo/React Native provide the runtime; `expo-camera` provides QR-only camera input; `expo-secure-store` protects the device credential at rest; `expo-haptics` gives nonvisual success/failure feedback; `expo-keep-awake` supports entrance-kiosk use; and `expo-status-bar` integrates the system bar. Expo Router, TanStack Query, Redux, audio, and offline-storage packages were not added.
- No database migration was required because scanner devices, attendance sessions/events, membership state, and occupancy inputs already had durable models.

## Acceptance traceability

| Requirement | Authoritative evidence |
|---|---|
| Separate scanner product boundary | `scanner-mobile/` has its own manifest, lockfile, entry point, configuration and tests; it has no member/admin routes or shared member-app navigation. |
| Device authentication and revocation | Existing constant-time hashed-key verification is reused; `/attendance/device/verify` and `app.cli.scanner_device provision/revoke` cover per-device lifecycle. |
| Server-derived safe success result | `ScannerResponse`, `AttendanceService.check_in/check_out`, and PostgreSQL integration assertions cover original fields, name, effective membership status, action, result status and occupancy while excluding contact/key/QR data. |
| Invalid, expired, superseded and ineligible QR outcomes | Integration tests assert malformed, expired, access-token-as-QR, superseded, inactive-membership, duplicate, already-active and no-active-session codes. |
| Concurrent attendance safety | PostgreSQL/Redis integration tests run concurrent check-in and checkout calls and prove one accepted transition and one durable active-session lifecycle. |
| Post-commit realtime behavior | Integration tests read committed session state inside the publication hook; publisher tests prove Redis failure is swallowed without logging its sensitive exception text. |
| Timeout/manual-close invalidation | Integration tests prove manual-close commit/audit/publication and two-member timeout batching with one final occupancy invalidation. |
| Authenticated, private WebSockets | Tests cover five-second authentication timeout, malformed/expired/forbidden closure, member isolation/own delivery, staff/manager/admin access, bounded queue overflow, heartbeat frames and reconnect resync. |
| Web authoritative refresh | Web tests prove attendance, dashboard and attendance-gated training roots refresh on attendance/occupancy/resync messages; unauthorized closure logs out; hidden/logout cleanup closes the socket; reconnect is bounded and jittered. |
| Member-mobile authoritative refresh | Mobile tests prove attendance, dashboard, QR and training roots refresh; background/logout cleanup closes the socket; unauthorized closure logs out; reconnect/resync and normal foreground Query focus provide recovery. |
| Scanner lifecycle and privacy | Scanner tests cover credential restoration/removal, explicit modes, permission/foreground camera gating, one in-flight scan, payload bounds, safe presentation, every stable error family, request IDs, reset clearing and absence of an offline QR queue. |
| Kiosk operation and distribution safety | Android export passes; generated output is ignored; identifiers remain explicit owner-approval placeholders; the runbook covers LAN/firewall, HTTPS/WSS, provisioning, revocation, retirement and troubleshooting. |

## Automated and local verification

| Area | Command or check | Result |
|---|---|---|
| Full backend | `docker compose -p ypgym-scanner-final-audit -f compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner --attach test-runner` | **199 passed**, 14 existing Starlette deprecation warnings |
| Focused attendance/realtime | Isolated attendance integration plus realtime unit files | **20 passed**, one existing Starlette warning |
| Final realtime unit | `docker compose exec -T backend-api pytest -q app/tests/test_attendance_realtime.py` | **11 passed**, one existing Starlette warning, including the final Redis reconnect and heartbeat assertions added after full-suite collection |
| Alembic | `alembic upgrade head` and `alembic check` in the backend container | Head reached; no new upgrade operations detected |
| Compose | `docker compose config --quiet` | Passed |
| Web | `npm test`, `npm run lint`, `npm run build` in `frontend/` | 26 tests passed; lint passed with one existing TanStack compiler warning; production/PWA build passed with the existing large-chunk warning |
| Member mobile | `npm test`, `npm run typecheck`, `npm run lint` in `mobile/` | 18 tests passed; typecheck and lint passed |
| Member Android export | `npx expo export --platform android --output-dir dist-scanner-realtime-check` | Passed; 1,710 modules bundled |
| Scanner app | `npm test`, `npm run typecheck`, `npm run lint`, `npm run export:android -- --output-dir dist-final-check` in `scanner-mobile/` | 12 tests passed; typecheck and lint passed; final Android export passed (602 modules) |
| Scanner install metadata | `npm ls --depth=0` and `npm ci --dry-run --ignore-scripts --no-audit --no-fund` | Passed |
| Provisioning CLI | `docker compose exec -T backend-api python -m app.cli.scanner_device --help` | Passed; `provision` and `revoke` commands available |
| Simulator compatibility | Valid check-in, duplicate, checkout, invalid-token, and unauthorized-device scenarios | 200, 409 `DUPLICATE_SCAN`, 200, 400 `INVALID_TOKEN`, and 401 `INVALID_DEVICE` respectively |
| Device verification | `POST /attendance/device/verify` with the local simulator device | 200; safe ID, display name, and active status only |
| WebSocket handshake | Authenticated member first-frame handshake | `subscribed` followed by required `resync_required` invalidation |
| Live realtime flow | Scanner-style check-in while listening through Redis/WebSocket | HTTP 200; received `attendance_changed` and `occupancy_changed`; cleanup checkout succeeded |
| Health | `GET /api/v1/health` | 200 |

Backend logs were inspected during live checks. No QR token, device key, access token, email, phone, or raw authentication frame was emitted by the new paths.

## Automated coverage highlights

- Safe scanner response data for check-in and checkout, compatibility fields, occupancy, post-commit publication, timeout and manual-close publication.
- Member event isolation, operations-role authorization, bounded queue overflow/resync, malformed/expired/forbidden WebSocket authentication, and Redis reconnect recovery.
- Web and mobile query invalidation, reconnect recovery, logout/foreground lifecycle behavior, and duplicate invalidation coalescing.
- Scanner SecureStore-boundary save/restoration/removal, permission and foreground camera gates, reducer transitions, one-request lock, explicit modes/checkout routing, safe success presentation, error-code guidance, network failure, API response parsing, request-ID display, reset clearing, and non-persistence of QR material.

## Physical-device gate not yet executed

A two-phone physical acceptance run was not available in this coding environment. This is the only remaining release evidence gate. Follow `docs/runbooks/scanner-mobile.md` using:

- Device A: the existing signed-in member app displaying a fresh rotating QR;
- Device B: the dedicated scanner app provisioned with a separately registered scanner device;
- an authorized browser attendance screen open at the same time.

Verify check-in, duplicate/already-active handling, checkout, expired/superseded/inactive cases, offline rejection with no queue, reconnect with a fresh QR, and foreground member/web refresh. Record the observed HTTP response and client refresh times; two seconds on a local network is a measurement target, not a guarantee.

## Owner actions before distribution

1. Replace the placeholder Android/iOS bundle identifiers and URL scheme in `scanner-mobile/app.json` with owner-approved values.
2. Use a trusted HTTPS/WSS deployment reachable by the entrance phone.
3. Replace development-only manual key entry with an expiring, single-use, owner-authorized provisioning exchange.
4. Produce and sign an owner-approved development or production build; do not distribute an Expo Go development session as a production kiosk.
5. Run and record the physical two-phone gate above.

No database model, migration, constraint, or durable state shape changed. Existing simulator clients remain compatible because all scanner response additions are optional additive fields.
