# Identity and membership email foundation

## Implemented contract

YPGym keeps one canonical `users` row and the existing JWT/RBAC system. `external_identities` stores only a provider key (`google` or `facebook`), immutable provider subject, email snapshot, provider verification assertion, login timestamps and revocation state. Provider email is never the identity key. A matching email on an unlinked YPGym account returns `ACCOUNT_LINK_REQUIRED`; the owner must sign in normally and connect the provider from Account Security. OAuth attributes can create only a `member` role.

Email/password registration, hashed one-time verification/reset records and password hashing remain unchanged. Provider-created users may have no password or phone. Google email is marked verified only when the validated ID token asserts `email_verified=true`. Facebook's profile response does not supply an equivalent verification assertion, so YPGym does not mark it verified. Facebook login requires a usable email and does not fabricate one.

OAuth state, PKCE verifier, Google nonce and final YPGym exchange codes live in Redis with short TTLs and are consumed once. The backend validates Google signature, issuer, audience, expiry, issued-at, nonce and subject against cached JWKS. Facebook exchanges the code server-side, validates the token with Meta's debug endpoint, checks app ID/user ID and fetches the minimum `id,name,email` profile with an app-secret proof. Provider access tokens are discarded. The browser/deep link receives only a short-lived YPGym exchange code, never a provider token, client secret or YPGym JWT.

Routes:

- `GET /api/v1/auth/providers`
- `GET /api/v1/auth/oauth/{google|facebook}/start?platform={web|mobile}`
- `GET /api/v1/auth/oauth/{provider}/callback`
- `POST /api/v1/auth/oauth/{provider}/exchange`
- `POST /api/v1/auth/oauth/{provider}/mobile/exchange`
- `GET /api/v1/account/identities`
- `POST /api/v1/account/identities/{provider}/link/start?platform={web|mobile}`
- `DELETE /api/v1/account/identities/{provider}`

Link/unlink requires a JWT issued within the configured recent-auth window. Unlink cannot remove the final usable method. If a provider later changes its email, YPGym updates only the provider snapshot; the canonical account email does not change.

## Redirect configuration

For local development with the documented ports, register these exact provider callback URIs:

- Google: `http://localhost:8001/api/v1/auth/oauth/google/callback`
- Facebook: `http://localhost:8001/api/v1/auth/oauth/facebook/callback`

The backend then returns web users to `http://localhost:5174/oauth/callback` and native users to `ypgym://oauth/callback`. Production `OAUTH_CALLBACK_BASE_URL` must be the exact HTTPS API origin plus `/api/v1`; set `FRONTEND_URL` to the exact HTTPS web origin. Do not register wildcard callbacks. Android/iOS package identifiers were not added or guessed; the current Expo app has the `ypgym` scheme but needs owner-approved native identifiers before store builds.

Provider environment names are listed in `backend/.env.example`: `OAUTH_CALLBACK_BASE_URL`, `GOOGLE_OAUTH_WEB_CLIENT_ID`, `GOOGLE_OAUTH_WEB_CLIENT_SECRET`, `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`, and `FACEBOOK_GRAPH_API_VERSION`. A provider is disabled when either its ID or server secret is empty. Clear both values and restart the API to disable a revoked provider safely; existing email/password or other linked methods continue to work.

## Purchase to email lifecycle

Migration `20260926_0013` adds `external_identities` and `email_deliveries`, and allows provider-created users to have null password/phone fields. A successful authoritative membership purchase or renewal creates the membership update, succeeded mock-payment record, immutable invoice/PDF and two email intents in the same PostgreSQL transaction:

1. `membership_purchase` or `membership_renewal` confirmation.
2. `membership_invoice` with the immutable PDF attached.

Each intent has a unique `template:invoice:recipient:version` key. Replaying the purchase idempotency key returns the existing payment/invoice and creates no more email rows. Celery runs `app.workers.send_membership_emails` each minute. PostgreSQL `FOR UPDATE SKIP LOCKED` claims due work; a committed `sending` lease prevents concurrent sends. Transient failures use bounded exponential retry with jitter; rejected recipients, exhausted attempts and exhausted stale claims become `failed`. A purchase is never rolled back because SMTP is unavailable.

Status meanings:

- `queued`: durable intent awaiting a worker.
- `sending`: claimed by one worker; stale claims can be recovered.
- `retrying`: transient failure with a future retry time.
- `sent_to_provider`: Maildir write or SMTP server acceptance succeeded; inbox delivery is not claimed.
- `failed`: permanent recipient failure or retry budget exhausted; eligible for manual retry.
- `cancelled`: reserved for an explicit future operator policy; workers do not send it.

Manager/admin route `/admin/email-deliveries` shows masked recipients, templates, invoice references, safe error categories and timestamps. `POST /admin/email-deliveries/{id}/retry` accepts only failed rows, is rate-limited, and writes an audit record. Existing admin-only billing ledger/export remains admin-only; managers reach the already-authorized member detail for transaction/invoice context.

## Local email and Gmail checkpoint

The default `EMAIL_DELIVERY_MODE=development` writes private messages to the ignored `backend/storage/mail/` Maildir. Run the worker task without displaying message contents:

```powershell
docker compose exec -T celery-worker celery -A app.workers.celery_app call app.workers.send_membership_emails
```

Real Gmail has not been tested. Configure the approved account directly in the untracked root `.env`, never in chat or Git:

```dotenv
EMAIL_DELIVERY_MODE=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS_MODE=starttls
SMTP_USERNAME=<approved YPGym Gmail address>
SMTP_PASSWORD=<Google App Password>
EMAIL_SENDER_NAME=YPGym Team
EMAIL_SENDER_ADDRESS=<approved YPGym Gmail address>
EMAIL_REPLY_TO=<optional monitored support address>
```

`SMTP_PASSWORD` is the project's equivalent of the prompt's `SMTP_APP_PASSWORD`; `SMTP_TLS_MODE=starttls` is its equivalent of `SMTP_STARTTLS=true`. Use a Google App Password, never the normal account password. Google's account guidance requires 2-Step Verification and says App Passwords can be unavailable for organization-managed, security-key-only or Advanced Protection accounts. If unavailable, use an owner-approved Gmail OAuth2 SMTP or transactional provider instead of weakening authentication. Revoke the App Password in the Google account and clear/restart the service during rotation.

## Privacy, limitations and references

Delivery rows retain the normalized recipient snapshot needed to send the invoice plus a masked display value, foreign keys, status and sanitized error class. They do not store message bodies, provider tokens, SMTP responses, credentials or stack traces. Access is role protected. Define a production retention/deletion period before deployment; deleting a user cascades these rows under the current account-deletion model.

Mocked provider and development Maildir coverage is implemented. Live Google, Facebook, Gmail, physical Android/iOS and production callback approval remain blocked on owner-managed credentials and provider-console setup. Meta's official documentation returned HTTP 429 to the implementation environment, so its configured graph version and setup must be rechecked at the credential gate before a live claim.

Protocol references checked on 2026-09-26:

- [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)
- [Google OAuth web-server flow](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google OAuth security practices](https://developers.google.com/identity/protocols/oauth2/resources/best-practices)
- [Google App Passwords](https://support.google.com/accounts/answer/185833)
- [Meta Facebook Login](https://developers.facebook.com/docs/facebook-login/)
