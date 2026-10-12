# Attendance-based membership renewal benefit

Feature 9 implements FR56 with the owner-approved **better-of** and **first successful renewal** policies.

## Rule

- The calculation uses the previous complete calendar month in `GYM_TIMEZONE` (default `Asia/Ho_Chi_Minh`), never a rolling 30-day window.
- The numerator is the authenticated member's distinct local calendar dates with an `iot_scanner` attendance session. Duplicate scans, staff-console entries and other members' visits do not count.
- The denominator is the actual number of days in that month. A result of at least 80% qualifies for a 10% renewal benefit.
- The member must have active or expiring-soon coverage whose expiry has not passed when checkout starts. Frozen, cancelled, revoked, expired and first-purchase flows do not receive the attendance benefit.
- The final discount is the larger of the membership plan discount and 10%; discounts never stack. If the plan discount is larger, it wins, while the qualifying attendance month is still consumed by the first successful renewal.
- A pending discounted checkout reserves the month. Failed, cancelled or expired payment releases it. A paid/succeeded renewal consumes it.

## API and clients

`GET /api/v1/memberships/attendance-benefit/me?plan_id=<uuid>` is member-only. Identity comes from the access token. It returns the period, distinct attended days, denominator, exact percentage, qualification/availability state and server-calculated price breakdown.

Possible states are `eligible`, `not_qualified`, `not_renewal`, `pending` and `consumed`. Web `/memberships/buy/:planId` and Expo `/(member)/renew/confirm` render this response and disable checkout while the server reports a reserved pending benefit. Payment results, billing history and invoices expose the immutable calculation snapshot.

Both VNPay checkout and the retained mock purchase endpoint calculate price on the backend. The client cannot supply attendance, discount or final amount.

## Persistence and concurrency

Migration `20261009_0017_attendance_renewal_benefit.py` adds:

- `payments.attendance_benefit_period_start`;
- JSON calculation snapshots on payments and invoices;
- a membership-product constraint; and
- a partial unique index for one pending/paid/succeeded benefit reservation per member and attendance month.

The payment, membership extension, invoice, snapshot, notification, email intents and audit record use the existing transaction. VNPay IPN replay and concurrent checkout cannot apply the benefit twice. Invoice regeneration reads the stored snapshot rather than recalculating historical attendance.

## Verification

`backend/app/tests/test_attendance_benefit.py` covers January/year rollover and 28/29-day February boundaries. `backend/app/tests/integration/test_attendance_benefit.py` covers the threshold, zero/below-threshold attendance, QR-only distinct days, cross-account isolation, frozen coverage, better-of pricing, plan-discount precedence, pending reservation, failed-payment release, successful consumption, concurrent checkout, mock renewal idempotency and invoice snapshots.
