# YPGym Finite State Machine Transition Tables

YPGym implements the **Finite State Machine (FSM) / State Transition Table Pattern** in `backend/app/services/state_transitions.py`. Each table declares valid state changes, and small transition functions reject undeclared changes with `InvalidStateTransitionError` before mutating an ORM entity.

The database continues to store strings. The Python `StrEnum` members in `backend/app/models/enums.py` improve type safety without changing the existing database representation or requiring an Alembic migration.

## Transition inventory

| Domain | Permitted transitions | Main side effects retained in service |
|---|---|---|
| Membership | `pending_verification -> active/expiring_soon/expired/frozen/cancelled/revoked`; `active -> expiring_soon/expired/frozen/cancelled/revoked`; `expiring_soon -> active/expired/frozen/cancelled/revoked`; `expired -> active/revoked`; `frozen -> active/expiring_soon/expired/cancelled/revoked` | Freeze dates, cancellation/revocation metadata, audit records, renewal coverage and expiry calculations. |
| Payment | `pending -> paid/failed/cancelled/expired/paid_review`; `failed/cancelled/expired -> paid_review` for a verified late class callback | VNPay signature and amount verification, row locks, invoices, membership activation, class confirmation, notifications, email outbox and audit records. |
| Class | `scheduled -> cancelled/completed` | Cancellation reason, affected bookings/waitlists, refund review and audit records. |
| Class booking | `pending_payment -> confirmed/cancelled/expired/payment_failed`; `confirmed -> cancelled`; `cancelled -> pending_payment/refunded`; `expired/payment_failed -> pending_payment/cancelled/refunded`; `refunded -> pending_payment` | Seat holds, capacity checks, timestamps, payment linkage, refunds, waitlist promotion and audit records. |
| Waitlist | `waiting -> promoted/cancelled`; `promoted/cancelled -> waiting` when the member becomes eligible to queue again | Position allocation, seat promotion and configuration limits. |
| Attendance | `active -> checked_out/timed_out/manual_closed` | Closure metadata, immutable attendance event, occupancy reconciliation and manual-close audit. |
| Approval request | `pending -> approved/rejected` | Reviewer identity, decision reason, outcome, membership changes and audit records. |
| Refund | `none -> required -> resolved`; `resolved -> none` when a resolved booking starts a new checkout | Refund review remains explicit and blocks checkout until staff resolves it. |

States without outgoing transitions are terminal. A repeated event is accepted only where the calling workflow explicitly requests idempotency. VNPay duplicate callbacks keep their existing early response, and attendance/membership APIs keep their existing domain-specific duplicate behavior.

## Legacy payment compatibility

`succeeded` remains a recognized, terminal legacy payment state. It is not silently rewritten to `paid`. Current VNPay transactions use `pending`, `paid`, `failed`, `cancelled`, `expired`, and `paid_review`. A cryptographically verified successful class callback received after failure, cancellation, or expiry can only move to `paid_review`, preserving manual financial resolution instead of restoring a seat implicitly.

## Concurrency and transaction boundary

The transition functions validate state only. The existing services remain responsible for row locks and atomic side effects:

- `backend/app/services/payment_service.py` locks payments, bookings, classes, and users during settlement.
- `backend/app/services/class_service.py` locks classes, bookings, and waitlist rows during cancellation and promotion.
- `backend/app/services/attendance_service.py` locks attendance sessions and relies on the unique active-session index.
- `backend/app/services/lifecycle_service.py` locks approval requests and memberships before decisions.

This separation keeps the table small while preserving the established endpoint → service → repository → model architecture.
