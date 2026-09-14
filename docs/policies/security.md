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

Current CORS allows configured FRONTEND_URL with credentials, without a wildcard. Environment files/generated storage are ignored. Example credentials are local development placeholders. Day55 remains in progress: final proxy/CORS denial checks, archive secret inventory, recovery edge cases and export review remain. Existing SMTP settings alone do not establish delivered-email support.
