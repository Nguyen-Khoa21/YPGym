# Independently paid class bookings

A verified member account may purchase one scheduled class seat without owning an active gym membership. Class entitlement and gym membership remain separate.

| Method | Route | Contract |
|---|---|---|
| `GET` | `/api/v1/classes/upcoming` | Scheduled sessions with server price, occupied/remaining seats, and caller state. |
| `POST` | `/api/v1/classes/{class_id}/checkout` | Create/reuse a bounded seat hold and pending payOS payment. Body: `idempotency_key` and `client_platform`; client prices are rejected. |
| `GET` | `/api/v1/payments/{payment_id}` | Owner-only authoritative payment, booking, refund, and invoice state. |
| `POST` | `/api/v1/bookings/{booking_id}/cancel` | Cancel before class start. A paid booking becomes `refund_required`; no automatic refund is claimed. |
| `POST` | `/api/v1/admin/classes/bookings/{booking_id}/check-in` | Operations roles record attendance for a confirmed seat without membership ownership. |
| `POST` | `/api/v1/payments/{payment_id}/resolve-class-refund` | Admin records a completed manual provider/bank resolution with reason and audit. |
| `POST` | `/api/v1/payments/payos/webhook` | Signed payOS server webhook and sole settlement authority. |

Checkout locks the class row, expires stale holds, preserves waitlist priority, checks confirmed seats plus live holds, snapshots the stored positive integer VND price, and creates a unique integer payOS `orderCode`. A repeated idempotency key for the same user/class returns the existing checkout; reuse for another product conflicts.

A verified successful webhook compares the immutable amount, currency, order, and payment-link mapping. In one transaction it confirms the seat, creates one invoice, queues confirmation and invoice messages once, creates the in-app notification, and audits fulfillment. Duplicate or concurrent deliveries do not repeat effects.

If money arrives after the hold expired or the class can no longer be fulfilled, the payment becomes `paid_review`; the booking remains unfulfilled and becomes `refund_required`. Staff complete any provider/bank action manually before recording resolution. Cancelling a whole class cancels live holds/waitlists and flags settled purchases for the same review. Historical legacy seats remain valid without fabricated charges.

See [payOS payments](payos-payments.md) for configuration, deployment, mocked tests, real-payment warnings, webhook registration, rollback, key rotation, and troubleshooting.
