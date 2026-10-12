# VNPay sandbox and Cloudflare Quick Tunnel runbook

This runbook starts the local YPGym stack, exposes only the backend callback port to VNPay, and exercises checkout from the React portal or Expo member app. Never paste or commit merchant secrets, signed payment URLs, session tokens, or SMTP credentials.

## 1. Start the API and create the public callback URL

From `C:\Users\Admin\ypgym`:

```powershell
docker compose --env-file backend/.env --profile app up -d --build
docker compose --env-file backend/.env exec -T backend-api alembic upgrade head
docker compose --env-file backend/.env exec -T backend-api python -m app.db.seed
Invoke-RestMethod http://localhost:8001/api/v1/health/dependencies
```

Keep a second PowerShell window open:

```powershell
cloudflared tunnel --url http://localhost:8001
```

Cloudflare prints a temporary `https://...trycloudflare.com` URL. Put that current origin into these existing `backend/.env` variables, preserving the exact paths:

```text
VNPAY_RETURN_URL=https://CURRENT-TUNNEL/api/v1/payments/vnpay/return
VNPAY_IPN_URL=https://CURRENT-TUNNEL/api/v1/payments/vnpay/ipn
```

Configure the same `VNPAY_IPN_URL` in the VNPay sandbox merchant/IPN settings when the portal requires a registered callback. The Return URL is embedded in each signed payment request. Quick Tunnel hostnames change whenever the tunnel is restarted, so update both settings before a new checkout.

Recreate the services after changing `backend/.env`; a reload alone does not update Compose environment values:

```powershell
docker compose --env-file backend/.env --profile app up -d --build --force-recreate backend-api celery-worker celery-beat
docker compose --env-file backend/.env exec -T backend-api alembic current
docker compose --env-file backend/.env exec -T backend-api alembic check
docker compose --env-file backend/.env ps
```

## 2. Test the React web portal

1. Open `http://localhost:5174` and sign in as a verified member.
2. Open Memberships, select an active plan, and choose **VNPay**.
3. Optionally select VNPay QR, a Vietnam bank, or an international card. The amount displayed by VNPay must match the YPGym plan price.
4. Complete or cancel the sandbox payment using VNPay-provided test data.
5. VNPay returns through the backend to `http://localhost:5174/app/payments/result`. Keep the page open while it waits for the signed IPN.
6. On success, verify the membership dates and open Billing for the new invoice.
7. As admin, open `http://localhost:5174/admin/billing` and verify provider, reference, status, settlement metadata, invoice, and email state.

## 3. Test the Expo member app

Expo web uses its own result route:

```powershell
cd C:\Users\Admin\ypgym\mobile
(Get-Content .env.example) -replace '^EXPO_PUBLIC_API_URL=.*$', 'EXPO_PUBLIC_API_URL=http://localhost:8001/api/v1' | Set-Content .env
npm ci
npx expo start --web --port 8081
```

Open the Expo preview, sign in as a verified member, then use Profile -> Membership Plan -> select a plan -> Continue to VNPay. Expo web returns to `http://localhost:8081/payment-result` and checks the same owner-only status API.

For Android/iOS development builds, set `EXPO_PUBLIC_API_URL` to a backend address the phone can reach. Native checkout returns to `ypgym://payment-result`; this requires the configured YPGym scheme in a development/production build. Expo Go cannot register YPGym's custom return scheme reliably, so close the VNPay browser after payment and return to the already-open result screen, or use an EAS development build.

## 4. Manual acceptance checklist

- **Success:** one `paid` payment, one membership activation/extension, one invoice, one queued/sent invoice email, one in-app notification, and one confirmation audit event.
- **Cancellation:** payment becomes `cancelled`; membership and invoices do not change.
- **Browser closed:** reopen the result screen or Billing. The IPN still settles independently of the browser.
- **Return before IPN:** result stays `pending`/processing until the status API observes the IPN.
- **IPN before Return:** result immediately shows the authoritative paid/final state.
- **Duplicate IPN:** provider receives the already-confirmed response; membership dates and invoice counts remain unchanged.
- **SMTP unavailable:** payment and membership stay confirmed; Admin Billing shows the outbox state and the Celery worker retries.
- **Renewal:** the existing active membership expiry extends by the selected plan's configured duration.
- **Simultaneous checkout:** each click may create a distinct pending transaction; only each transaction's first verified successful IPN can create its effects. The UI disables its button while creation is in flight and the API rate limits bursts.
- **Ownership:** a second member cannot read the first member's transaction ID.
- **Tampering:** invalid signature, amount, or transaction reference must not change payment or membership. Use the automated integration test for safe tamper testing rather than editing live signed URLs.

## Troubleshooting

- **VNPay cannot reach IPN:** keep `cloudflared` running, confirm the tunnel URL is current, and open `https://CURRENT-TUNNEL/api/v1/health` before checkout.
- **VNPay opens but result stays pending:** verify the sandbox merchant IPN setting, inspect sanitized API logs, and check the transaction in Admin Billing. Do not mark it paid manually based only on the browser Return.
- **API says VNPay is disabled/incomplete:** verify the VNPay variable names in `backend/.env`, then recreate `backend-api` as shown above.
- **Expo web returns to the React portal:** restart the backend and Expo after updating the current code/environment. Expo checkouts identify themselves as `mobile_web`.
- **Native app does not reopen:** use a YPGym EAS development build with the `ypgym` scheme, or return manually to the result screen in Expo Go.
- **Email remains queued/retrying:** inspect the worker state and existing admin email-delivery controls; do not repeat payment to resend an invoice.

Stop the Quick Tunnel with `Ctrl+C`. Its hostname is temporary and must never be treated as a production endpoint.
