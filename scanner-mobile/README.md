# YPGym Scanner

This is the dedicated Expo SDK 58 entrance scanner. It is intentionally separate from the member app in `mobile/` and contains no member, billing, class, training, CRM, or administration screens.

## Install and run on a physical phone

1. Start YPGym's backend and seed data from the repository root.
2. Copy `.env.example` to `.env` and replace the example host with the computer's LAN IPv4 address. Keep `/api/v1` in the URL.
3. Install dependencies and start Expo on the LAN:

```powershell
cd C:\Users\Admin\ypgym\scanner-mobile
Copy-Item .env.example .env
npm ci
npx expo start --lan
```

4. Open the QR with an Expo Go version compatible with SDK 58. The phone and computer must be able to reach each other; guest Wi-Fi client isolation may prevent this even when both devices show the same Wi-Fi name.
5. Provision the app with the API base URL, one registered device ID, its private device key, and the allowed scanner mode. The manual form is for controlled development/testing, not production enrollment.
6. Grant camera permission. Choose Check in or Check out, then scan the member app's current My QR code.

The scanner never stores member QR tokens or scan history and never queues offline attendance. Long-press the **YPGym Scanner** title for 1.8 seconds to remove this phone's stored device credentials.

## Quality checks

```powershell
npm test
npm run typecheck
npm run lint
npm run export:android
```

Before store distribution, the owner must replace the placeholder Android/iOS identifiers and URL scheme in `app.json`. Production also requires HTTPS/WSS, managed one-time provisioning, an owner-approved application identifier, and a signed development/production build rather than Expo Go.

Operational provisioning, firewall, troubleshooting, revocation, and two-device acceptance steps are in [`docs/runbooks/scanner-mobile.md`](../docs/runbooks/scanner-mobile.md).
