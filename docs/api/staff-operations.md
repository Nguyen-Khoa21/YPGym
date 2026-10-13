# Staff accounts and time clock

Feature 10 implements FR43–FR44 with the existing YPGym user, role, password and audit infrastructure.

## Account provisioning

Managers and administrators can list and create workforce accounts through:

- `GET /api/v1/admin/staff-accounts`
- `POST /api/v1/admin/staff-accounts`

The create contract accepts a full name, unique login name, optional phone number and only `staff` or `pt`. The server appends `STAFF_ACCOUNT_EMAIL_DOMAIN`, hashes a cryptographically generated 20-character temporary password immediately and returns the plaintext password only in the one successful manager-only response. It is never stored, listed, logged or written to audit data.

New accounts are internally verified because the configured domain is an authentication namespace. `ypgym.dev` remains a local demo domain and is not claimed to receive email. Configure a domain owned by YPGym before adding staff email delivery.

A new PT account receives a linked active `personal_trainers` profile in the same transaction. Managers can finish its public specialty, availability and biography in `/admin/pt-assignments`. The provisioning route cannot create manager or administrator roles.

Every new account has `must_change_password=true`. Login succeeds only far enough to reach `/change-password`; other protected endpoints return `PASSWORD_CHANGE_REQUIRED`. The existing authenticated password-change service verifies the temporary password, hashes the replacement and clears the gate.

## Staff shifts

Staff and PT users use:

- `GET /api/v1/staff/shifts/me`
- `POST /api/v1/staff/shifts/clock-in`
- `POST /api/v1/staff/shifts/clock-out`

Timestamps come from the server in UTC. A PostgreSQL partial unique index permits one open shift per user, while a locked user row serializes concurrent clock-in requests. Clock-out requires an open shift and must be later than clock-in. Each successful clock action writes an audit record in the same transaction.

Managers and administrators use paginated `GET /api/v1/admin/staff-shifts` with name/login, role, open/closed and local-date filters. Date boundaries are converted from `GYM_TIMEZONE` to UTC on the server. API timestamps remain ISO UTC values; the web renders them in the returned gym timezone.

Shift corrections are intentionally unavailable in Feature 10. Persisted timestamps remain immutable through the public API rather than exposing an unaudited edit path.

## Security boundaries

- Only manager/admin can provision and report across accounts.
- Only staff/PT can operate their own time clock; identity always comes from the access token.
- Temporary passwords never appear in lists, audits or later responses.
- Shared seeded `staff@ypgym.dev` and `pt@ypgym.dev` accounts remain development demonstrations. Managers can create distinct workforce accounts for actual testing.
- No workforce email delivery is claimed for the internal login domain.
