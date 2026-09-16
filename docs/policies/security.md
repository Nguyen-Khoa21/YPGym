# Security controls

PostgreSQL remains authoritative for users, roles and durable transactions; Redis holds replaceable short-lived controls.

## Sensitive endpoint limits

| Family | Scope | Limit / window |
|---|---|---|
| Login | Hashed client IP; also hashed IP + normalized email | 60/minute per IP; 10/minute per pair |
| Forgot password | Hashed client IP; also hashed IP + normalized email | 20/15 minutes per IP; 5/15 minutes per pair |
| Scanner check-in/out combined | Hashed IP before authentication; hashed device ID after valid active-device credentials | 120/minute per IP; 60/minute per authenticated device |

Redis Lua combines the bounded counter and expiry atomically and repairs keys missing expiry. Denials do not extend windows. Over-limit responses are 429 with Retry-After and matching error details; Redis failures return 503 before sensitive work. Invalid credentials cannot consume a device's authenticated budget. Varying email cannot bypass the IP guard. Counters contain no raw passwords, addresses, tokens or QR material.

Limits use the client address provided by ASGI. Any deployment behind a proxy must explicitly configure trusted proxies and verify address attribution. Shared NATs share a budget. The local benchmark retains these controls.

## Credentials, tokens and errors

- New JWTs have type=access. Signed legacy tokens with subject, role, tier and expiry remain valid until existing expiry. Other token purposes, including actual attendance QR tokens, cannot authorize account access. Backend roles come from PostgreSQL, not the signed role claim.
- QR tokens require their own purpose, expiry and live Redis rotation state. Check-in also requires eligible membership and valid active-device credentials.
- Validation details include only location, type and message, without rejected input/context. Generic errors expose no internal exception values. Failure logs retain exception type and request metadata without exception text/SQL parameters. Request IDs are normalized UUIDs.
- Uvicorn access logging is disabled because its URLs can include query tokens. Application middleware records paths/status/timing without query strings or bodies.
- Development registration/reset messages use the ignored backend/storage/mail/new/ Maildir outbox, configurable with DEVELOPMENT_MAIL_DIR. Private links are not logged; PostgreSQL stores their hashes. Protect and exclude this outbox from archives. Test environments skip development messages. External SMTP delivery is not implemented by this local workflow.

## Verification and remaining review

The standalone compose.test.yml suite covers real Redis races/expiry, IP-email variation, scanner credential budget isolation, Redis outage, five roles, QR/access-token separation, missing/expired JWTs, registration/reset and record ownership. Local outbox and error-log privacy tests supplement it. See docs/release/integration-report.md.

Current CORS allows configured `FRONTEND_URL` and explicit `CORS_EXTRA_ORIGINS` with credentials, without an origin wildcard. September 16 live demo preflights accepted `http://localhost:55174` and `http://localhost:8081` with exactly the requested allowed origin; `https://untrusted.example` returned 400 without `Access-Control-Allow-Origin`. CORS controls browser reads; it does not replace endpoint authentication or apply to native networking.

The installed demo Uvicorn configuration reports proxy headers enabled with only `127.0.0.1` trusted. Endpoints derive limiter keys from `request.client.host`, never directly from arbitrary forwarded headers. An external proxy is not configured in this local release. Before deploying behind one, set its exact trusted address range, verify forwarded-client attribution over that actual network path, and exclude direct access to the API. Do not enable wildcard proxy trust as a performance workaround.

The 101-test isolated suite now covers admin-only CRM/payment/invoice CSV permissions, exact filters, empty results, leading-whitespace formula escaping, export audits and configuration validation/cache invalidation. Environment files/generated storage are ignored; a tracked-file path inventory found only the four environment examples, no actual environment files, private key files, generated storage or dependency directories. This path check does not establish a full secret-content scan or reviewed release archive.

## September 16 frontend dependency patches

Compatible `npm audit fix` updated the existing frontend lockfile without changing direct dependency major lines or adding/removing packages from the manifest. Fresh host `npm ci` and the rebuilt demo frontend image both installed Vite 7.3.6; the host also confirmed React Router 7.18.4 and PostCSS 8.5.28 directly from their installed package files. Host lint/build and `npm audit` passed; npm reported zero vulnerabilities after the fresh install. Existing TanStack compiler and 739.62 kB bundle warnings remain.

Vite's advisory describes a Windows development-server path restriction issue; the updated version exceeds its patched 7.3.5 line. React Router's advisory applies specifically to unstable RSC support; this SPA does not claim that integration. Sources: [Vite advisory](https://github.com/vitejs/vite/security/advisories/GHSA-fx2h-pf6j-xcff), [React Router advisory](https://github.com/remix-run/react-router/security/advisories/GHSA-qwww-vcr4-c8h2), [npm audit workflow](https://docs.npmjs.com/cli/v11/commands/npm-audit/).

The earlier host build still loaded the old physical Vite files despite the updated lock metadata; only the later fresh `npm ci` and Vite 7.3.6 build count as patched host validation. This frontend audit is separate from the documented Expo transitive advisories and does not prove that every backend/runtime dependency is vulnerability-free.

Day55 implementation and local verification are complete. The remaining Day60 work is the reviewed source archive and local release commit/tag; deployed proxy-path verification is outside the authorized local scope. Existing SMTP settings alone do not establish delivered-email support.
