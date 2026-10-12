# Independently paid class bookings

YPGym sells one seat in one scheduled class as a product separate from membership. A verified, signed-in member account can buy a class without an active gym membership. The class purchase never creates or extends a membership, and a membership purchase never confirms a class.

## API contract

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/classes/upcoming` | List scheduled sessions with server price, occupied seats, remaining seats, and the caller's booking state. |
| `POST` | `/api/v1/classes/{class_id}/checkout` | Create or reuse a 15-minute seat hold and pending VNPay payment. Body: `idempotency_key`, optional `locale`, `bank_code`, and `client_platform`. Client prices are rejected. |
| `GET` | `/api/v1/payments/{payment_id}` | Read the authoritative payment, booking, refund, and invoice state for the owner. |
| `POST` | `/api/v1/bookings/{booking_id}/cancel` | Cancel before the class starts. A settled paid booking becomes `refund_required`; no automatic VNPay refund is claimed. |
| `POST` | `/api/v1/admin/classes/bookings/{booking_id}/check-in` | Staff, manager, or admin records attendance for a confirmed seat. Membership is not required for that class entitlement. |
| `POST` | `/api/v1/payments/{payment_id}/resolve-class-refund` | Admin records a completed manual refund/resolution with a required reason and audit entry. |
| `GET` | `/api/v1/payments/vnpay/ipn` | VNPay server callback. This is the only callback that settles a payment. |
| `GET` | `/api/v1/payments/vnpay/return` | Validates the browser return signature and redirects to the UI; it does not settle a payment. |

Authorized admin class create/update requests include `price_vnd`, a positive integer number of VND. Updating a future session price does not change existing booking or payment snapshots.

## Lifecycle and capacity

Checkout locks the class row, expires old holds, checks `confirmed` bookings plus live `pending_payment` holds against capacity, snapshots `classes.price_vnd`, and creates one pending payment. The `(user_id, idempotency_key)` payment constraint makes a repeated click return the same transaction. Celery's pending-payment expiry task releases abandoned holds, and checkout also expires holds transactionally before counting seats.

A valid IPN checks the HMAC signature, merchant code, stored reference, stored amount, provider result, and stored product link. Settlement dispatches by the database `product_type`. In one database transaction it marks a class payment paid, confirms the booking, issues one invoice, queues class confirmation and invoice messages, creates an in-app notification, and writes an audit entry. Duplicate callbacks return an already-processed response and do not repeat fulfillment.

If money arrives after the hold expired, or the seat can no longer be fulfilled, the payment becomes `paid_review`; the booking remains unfulfilled and is marked `refund_required`. Admins resolve it from `/admin/billing` after completing the refund or other manual provider action. YPGym records the resolution but does not call an automated VNPay refund API.

Cancelling a whole session cancels live holds and waitlist entries. Paid confirmed seats are flagged `refund_required`; legacy seats are cancelled without inventing a charge. A rescheduled session keeps its booking entitlement and immutable paid price. Member cancellation is allowed until the class starts. A confirmed class seat permits class check-in for a non-member, while ordinary gym QR access remains membership-controlled.

## Migration and historical records

Migration `20261005_0016_paid_class_bookings.py` adds class price snapshots, paid-booking lifecycle fields, product-discriminated payments/invoices, and class email references. Existing membership payments/invoices are backfilled as `membership`. Existing `booked` class rows become `confirmed` with `entitlement_source=legacy`, no fabricated payment, and no fabricated price. Downgrade is blocked after class payments exist because dropping them would lose paid-product data.

## Sandbox verification

1. Set the VNPay placeholders in `backend/.env`. Keep the secret only in that ignored file.
2. Start a Cloudflare Quick Tunnel to local backend port `8001`.
3. Set both `VNPAY_RETURN_URL` and the VNPay merchant IPN URL to the current HTTPS tunnel hostname with `/api/v1/payments/vnpay/return` and `/api/v1/payments/vnpay/ipn` respectively. Quick Tunnel hostnames change after restart.
4. Recreate `backend-api`, `celery-worker`, and `celery-beat` with `docker compose --env-file backend/.env --profile app up -d --build`.
5. As admin, open `/admin/classes`, create a future session with a VND price, then sign in as a verified member account and open `/app/classes`.
6. Select **Book & pay**, finish a VNPay sandbox payment, and let the browser return to the result page. Confirm it reaches `confirmed`, then inspect `/app/bookings`, `/app/billing`, and `/admin/billing` with product filter **Class bookings**.

Automated tests use signed local callback fixtures. They verify application settlement logic; they do not prove that external VNPay sandbox credentials, callbacks, or network access are currently available.
