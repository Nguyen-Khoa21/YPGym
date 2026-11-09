# payOS VietQR payments

payOS is YPGym's active payment provider for membership purchases and independently paid class bookings. The former VNPay sandbox integration is retired. Historical database rows with `provider = 'vnpay'` are retained for financial/audit history, but no VNPay route, signing code, configuration, or checkout is active.

## Prerequisites and configuration

Create and verify a payOS account, create a payment channel, and link the bank account that should receive VietQR/Napas 24/7 transfers. Configure these backend-only variables in ignored `backend/.env` or the deployment secret manager:

```env
PAYOS_ENABLED=true
PAYOS_CLIENT_ID=
PAYOS_API_KEY=
PAYOS_CHECKSUM_KEY=
PAYOS_RETURN_URL=https://web.example.com/payment/payos/success
PAYOS_CANCEL_URL=https://web.example.com/payment/payos/cancel
PAYOS_WEBHOOK_URL=https://api.example.com/api/v1/payments/payos/webhook
PAYOS_TRANSACTION_TTL_MINUTES=15
PAYOS_TIMEOUT_SECONDS=10
```

The three credentials are secrets. Never put them in Vite/Expo variables, logs, screenshots, tests, documentation, or source control. Return/cancel URLs are browser UX only. Development may use `http://localhost` or another loopback address for those two URLs. The webhook must always use public HTTPS; localhost, LAN addresses, and random Quick Tunnel hosts are not production configuration.

## API and authority

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/v1/payments/payos/create` | Authenticated membership checkout using the plan and price loaded from PostgreSQL. |
| `POST` | `/api/v1/classes/{class_id}/checkout` | Authenticated independent class checkout using the stored class price and a locked capacity hold. |
| `POST` | `/api/v1/payments/payos/webhook` | Public payOS server webhook; its SDK-verified signature is the payment authority. |
| `GET` | `/api/v1/payments/payos/{order_code}` | Owner-only local authoritative state by payOS order code. |
| `GET` | `/api/v1/payments/{payment_id}` | Owner-only local authoritative state by internal UUID. |

The backend obtains a unique integer `orderCode` from PostgreSQL, creates the pending attempt, calls the official async payOS SDK, then stores the payment-link identifier and checkout URL. The client receives only safe checkout data. Amount, product, ownership, membership eligibility, class availability, and entitlement are never accepted from the client.

The webhook verifies the signature before reading its fields, locks the payment row, compares exact integer VND amount/currency/payment-link identifiers, and processes success once. In the same transaction it marks the payment paid, activates/extends membership or confirms one class seat, creates one invoice, queues deduplicated receipt messages, creates the notification, and writes the audit record. Duplicate/concurrent delivery is idempotent. A verified payment received after expiry/cancellation/failure becomes `paid_review`; it does not silently restore an entitlement.

Browser success/cancel pages query these authenticated status endpoints. A copied or modified success URL never marks a payment paid.

## Local and automated development

payOS has no sandbox. Automated tests mock payment-link creation and use locally signed webhook fixtures; they never contact payOS or transfer money. Keep `PAYOS_ENABLED=false` when working without configured credentials. Apply migrations before starting the new backend:

For a local-only controlled payment test, keep the browser callbacks local and expose only the backend webhook through a temporary tunnel:

```env
PAYOS_RETURN_URL=http://localhost:5174/payment/payos/success
PAYOS_CANCEL_URL=http://localhost:5174/payment/payos/cancel
PAYOS_WEBHOOK_URL=https://your-temporary-tunnel.example/api/v1/payments/payos/webhook
```

Keep the tunnel process running and update both `backend/.env` and the payOS channel whenever its temporary hostname changes. This is for local testing only, not production.

Apply migrations before starting the new backend:

```powershell
docker compose --env-file backend/.env --profile app up -d --build
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api alembic current
docker compose exec -T backend-api alembic check
```

The health response reports only whether payment configuration is `ready` or `disabled`; it never exposes values.

## Webhook deployment and registration

Route the stable API hostname through the existing TLS/reverse-proxy/Cloudflare Tunnel deployment to `backend-api`. Preserve the POST method and body and do not add browser authentication redirects to `/api/v1/payments/payos/webhook`. After deployment, register `PAYOS_WEBHOOK_URL` in the payOS channel dashboard (or use the official confirmation operation). payOS sends a signed sample payload during confirmation; YPGym verifies it and safely acknowledges an unknown sample order without creating data.

Restart the API after secret/config changes. Workers need rebuilding when application code changes. Rotate a key in the payOS dashboard, replace the backend secret, recreate the API, and verify health/webhook delivery; never run old and new checksum keys interchangeably. Rollback requires disabling checkout, restoring the prior application image, and downgrading migration `20261103_0019` only if no payOS-linked rows must be retained. Downgrade removes payOS mapping fields, so back up and review financial data first.

## Refunds and reconciliation

YPGym records manual refund resolution; it does not claim an automatic payOS refund. Staff must complete the provider/bank-side action before marking the audited exception resolved. Local PostgreSQL state is authoritative to clients. Provider lookup is available inside the payOS client for controlled reconciliation work, but it is not a client-controlled paid-state mutation.

## Troubleshooting

- Invalid signature: confirm the channel checksum key and that the proxy forwards the body unchanged; rotate any exposed key.
- Unreachable webhook: verify public DNS/TLS, proxy POST routing, firewall rules, and payOS dashboard registration.
- Amount/link mismatch: do not edit the payment; investigate the local attempt and provider event as a security/financial exception.
- Duplicate delivery: a 2xx response with no duplicate invoice/entitlement/email is expected.
- Expired link: allow the local expiry task to release the attempt/seat, then create a new checkout.
- Pending confirmation: refresh the owner status endpoint; do not treat the return URL as success or start a second payment until the first is final.

## Controlled real-payment acceptance

No automated command performs this test. With owner approval, use the smallest practical amount (about 2,000–10,000 VND) and verify: the checkout item/amount/recipient; funds reaching the linked bank account; signed webhook receipt; one paid payment/invoice; exactly one membership/class entitlement; exactly one receipt delivery; updated web/mobile/admin state; replay/refresh idempotency; and honest cancellation/expiry behavior.

## Gym location

Every payOS payment stores the gym it was created for. Membership checkout requires an active gym for a first purchase, and the member's home gym changes only after the verified webhook. See [gym-scoped-services.md](gym-scoped-services.md).
