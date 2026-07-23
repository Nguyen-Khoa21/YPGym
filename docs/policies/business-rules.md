# Business Rules through Day 42

## Membership and billing

- Plans, duration, discounts, prices, and benefits come from PostgreSQL.
- VND is the single application billing currency. Seeded plans range from 720,000 VND for one month to 16,200,000 VND for three years; web amounts use Vietnamese currency formatting and invoice PDFs use the ASCII `VND` prefix.
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

## Trainers, classes, booking, and waitlist

- Admin class creation/update requires timezone-aware future start, end after start, capacity 1-500, valid active trainer when assigned, and no trainer/location overlap.
- Cancellation is a reasoned, audited status transition; rows are not hard-deleted.
- Manager/admin trainer profile changes are audited. Public/member responses expose only name, bio, specialty, availability, active state, and bounded upcoming classes.
- Trainer deactivation is blocked while a scheduled future class is assigned; historical rows are never deleted.
- An active or expiring-soon effective membership is required to book or join a waitlist. Frozen, pending-verification, expired, cancelled, revoked, and absent memberships are ineligible.
- Booking, waitlist allocation, cancellation, and promotion lock the class row, so concurrent requests cannot overbook capacity or allocate the same queue position.
- A member cannot hold both a confirmed booking and a waiting entry for one class. Existing cancelled rows are safely reactivated instead of bypassing database uniqueness.
- Waitlist join is available only when the class is full and the configured `waitlist_size` is not exhausted.
- Cancellation is allowed at the exact configured cutoff and rejected after it. Started, completed, or administratively cancelled classes cannot use member cancellation.
- Cancellation frees capacity and automatically promotes the earliest eligible waiting entry in the same transaction. Ineligible entries transition to cancelled and the scan continues.
- Promotion notifications respect general in-app/email preferences and use channel-specific dedupe keys.
