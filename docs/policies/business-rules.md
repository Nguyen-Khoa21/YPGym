# Business Rules through Day 38

## Membership and billing

- Plans, duration, discounts, prices, and benefits come from PostgreSQL.
- Purchase is development/mock payment only and is idempotent per user and idempotency key.
- A successful payment has one immutable invoice record and downloadable PDF.
- Lifecycle rules are defined in `membership-lifecycle.md`; approved refund/credit outcomes are records, not real settlement.

## Notifications and broadcasts

- Members control email, in-app, expiry-reminder, and broadcast preferences.
- Expiry reminders target 7, 3, and 1 day before expiry and use unique dedupe keys per membership/date/day/channel.
- Broadcasts require audience, title, message, start, optional end, creator, and active state. Active member delivery respects tier/audience, time window, and preferences.

## Operational configuration

| Key | Safe range | Default |
|---|---:|---:|
| `gym_capacity` | 1-5000 | 150 |
| `qr_token_ttl_seconds` | 15-300 | 60 |
| `attendance_timeout_minutes` | 15-1440 | 180 |
| `duplicate_scan_window_seconds` | 1-300 | 30 |
| `class_cancellation_window_hours` | 0-168 | 12 |
| `waitlist_size` | 0-100 | 10 |

Values are persisted, centrally validated, cached in Redis, invalidated on update, and audited.

## QR, scanner, attendance, and occupancy

- Only eligible members receive signed, short-lived, rotating QR JWTs. A new JTI supersedes the prior token.
- Registered devices authenticate with ID and API key; the database stores only a key hash.
- Stable scanner failures distinguish invalid device, invalid/expired/superseded token, inactive membership, duplicate scan, existing/no active session, and dependency failure.
- PostgreSQL enforces one active session per user. Closure occurs by scanner checkout, configured timeout, or reasoned staff/manager/admin manual close.
- PostgreSQL active-session count is authoritative. Redis caches the derived response for 30 seconds and is reconciled after session changes.
- Thresholds: Low <=30%, Moderate <=60%, Busy <=85%, Very Crowded >85%.

## Classes and later booking boundary

- Admin class creation/update requires timezone-aware future start, end after start, capacity 1-500, valid active trainer when assigned, and no trainer/location overlap.
- Cancellation is a reasoned, audited status transition; rows are not hard-deleted.
- Day 37 provides booking/waitlist tables and integrity constraints. Member booking, capacity enrollment, cancellation-window enforcement, promotion, and PT management are explicitly Day 39-41 scope.
