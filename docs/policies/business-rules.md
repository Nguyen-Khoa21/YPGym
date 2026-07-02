# Business Rules Baseline

## Membership Plans

- Plans should be seeded from PostgreSQL, not hardcoded in the frontend.
- Supported initial durations: 1 month, 3 months, 6 months, 1 year, 2 years and 3 years.
- Discount and price display should come from the API so web and mobile stay consistent.

## Freeze

- Freeze requests require a reason and must follow the configured minimum and maximum period.
- Freeze fee and medical waiver behavior should be stored as configuration before implementation.

## QR and Attendance

- QR tokens are short-lived and stored or tracked in Redis by token ID/hash.
- Duplicate active sessions for the same member are blocked.
- Occupancy must decrease through check-out, timeout or staff/admin manual close.

## Classes and Waitlist

- Inactive memberships cannot book classes.
- Full classes offer waitlist join.
- Waitlist order is timestamp-based.
- Cancellation window and waitlist promotion behavior must be configurable.

