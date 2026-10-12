# VNPay membership payments

YPGym uses VNPay for member purchase and renewal checkout. The existing payment, membership, invoice, notification, audit, email-outbox, Celery, and admin-billing layers remain the system of record.

## Flow and authority

1. An authenticated member selects an active plan. `POST /api/v1/payments/vnpay/create` loads its price and duration from PostgreSQL, creates a `pending` payment, commits it, and returns a backend-signed VNPay 2.1.0 URL.
2. The web portal or Expo app opens that URL. No secret or authoritative price is stored in either client.
3. VNPay calls public `GET /api/v1/payments/vnpay/ipn`. The backend allowlists fields, verifies HMAC-SHA512, merchant code, exact transaction reference, and the integer VND protocol amount. Both `vnp_ResponseCode` and `vnp_TransactionStatus` must be `00`.
4. The IPN locks the payment row. One PostgreSQL transaction changes it to `paid`, activates or extends membership, creates one immutable invoice, enqueues one invoice email, creates one in-app notification, and records one audit event. A duplicate or concurrent delivery returns `02` and repeats no effects.
5. `GET /api/v1/payments/vnpay/return` verifies the signature and redirects to a configured result screen. It never changes payment, membership, invoice, or email state.
6. The authenticated result screen reads `GET /api/v1/payments/{transaction_id}`. Ownership is enforced by the query; another member receives `404`. Pending results poll every two seconds for no more than 30 seconds and can be checked again safely.

The payment state transitions are `pending -> paid | failed | cancelled | expired`. Final states never return to `pending`. Legacy mock records retain `succeeded` for compatibility and continue to appear in billing history.

## Persistence

Migration `20260929_0015` extends `payments` with the provider transaction data. It retains existing rows, derives their integer VND amount, and labels them with the `mock` provider. PostgreSQL enforces a positive integer amount, unique `txn_ref`, and a unique `(provider, provider_transaction_no)` when the provider reference is present. Downgrade preserves rows by mapping `paid` to the legacy `succeeded` status and other new terminal/pending states to legacy `failed` before dropping provider-only columns.

All provider amounts are stored as integer VND. The database amount is multiplied by 100 exactly once for `vnp_Amount`. Dates used in the VNPay protocol are generated in `Asia/Ho_Chi_Minh`; stored timestamps remain timezone aware.

## Routes and roles

| Route | Access | Purpose |
|---|---|---|
| `POST /api/v1/payments/vnpay/create` | Authenticated member | Create one pending checkout from an active database plan |
| `GET /api/v1/payments/vnpay/ipn` | Public, signed by VNPay | Authoritative and idempotent settlement |
| `GET /api/v1/payments/vnpay/return` | Public, signed by VNPay | Safe navigation only |
| `GET /api/v1/payments/{transaction_id}` | Owning member | Authoritative result and invoice status |
| `GET /api/v1/admin/billing/payments` | Existing admin permission | Provider, reference, settlement metadata, invoice and email state |

The admin billing CSV contains the same filtered fields and remains audited. Manager/staff billing access is unchanged and denied by the existing permission policy.

## Configuration

Server-only variables:

- `VNPAY_ENABLED`
- `VNPAY_ENVIRONMENT`
- `VNPAY_TMN_CODE`
- `VNPAY_HASH_SECRET`
- `VNPAY_PAYMENT_URL`
- `VNPAY_API_URL`
- `VNPAY_RETURN_URL`
- `VNPAY_IPN_URL`
- `VNPAY_TRANSACTION_TTL_MINUTES`
- `FRONTEND_PAYMENT_RESULT_URL`
- `MOBILE_PAYMENT_RESULT_URL`

`MOBILE_WEB_URL` supplies the Expo-web result origin. VNPay is auto-enabled when both merchant code and hash secret are present; `VNPAY_ENABLED=false` explicitly disables it. Enabled configuration fails fast when required values are absent, the merchant code is invalid, or provider/callback URLs do not use HTTPS. Production rejects the sandbox payment endpoint.

Sandbox uses the VNPay sandbox payment and query hosts and a temporary HTTPS tunnel for local callbacks. Production requires permanent HTTPS callback URLs, production credentials, provider approval, monitoring, and an operational reconciliation policy.

## Security and operations

- `VNPAY_HASH_SECRET` is read only by the backend and is never returned or logged.
- The create body forbids unknown fields, so a client-supplied amount is rejected.
- Client IP comes from the ASGI request after the project's trusted-proxy configuration; arbitrary query/header input is not used.
- Raw callback queries and complete signed checkout URLs are not logged.
- Pending creation is rate limited per authenticated user.
- Expired pending rows are marked by the existing Celery beat/worker infrastructure and opportunistically on owner status reads.
- Email is delivered after commit through the existing durable outbox. SMTP retry cannot undo payment, membership, or invoice state.

VNPay query/reconciliation and refunds are intentionally not implemented because the repository had no provider reconciliation/refund subsystem. Add them as separate guarded payment transitions with audited operator permissions before production use.

See [the sandbox runbook](../runbooks/vnpay-sandbox.md) for startup and manual verification.
