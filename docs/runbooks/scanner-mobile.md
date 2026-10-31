# Dedicated scanner phone runbook

## 1. Start the authoritative services

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app up -d --build
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api python -m app.db.seed
```

Confirm `http://localhost:8001/api/v1/health` on the computer. A physical phone cannot use the computer's `localhost`; use the computer's reachable LAN IPv4 address, for example `http://192.168.1.100:8001/api/v1`. Android Emulator uses `http://10.0.2.2:8001/api/v1`. Guest/coffee-shop Wi-Fi often isolates clients, so a private router or phone hotspot is preferable. Allow inbound TCP 8001 and the Expo/Metro ports in Windows Firewall only on the trusted private network.

Local HTTP/WS is for trusted development only. Production device traffic and realtime client traffic require HTTPS/WSS with a trusted certificate.

## 2. Provision one independent device

Choose a unique device ID and a high-entropy key of at least 24 characters. Run inside the backend container; input is hidden and the key is never printed or stored in plaintext:

```powershell
docker compose exec backend-api python -m app.cli.scanner_device provision front-door-1 "Front door scanner"
```

Enter the same key once in the scanner's first-run form. Successful server verification stores it in SecureStore on that phone. Do not put it in `.env`, `EXPO_PUBLIC_*`, source control, screenshots, chat, or a distributable binary.

To revoke only this phone without changing other scanners:

```powershell
docker compose exec -T backend-api python -m app.cli.scanner_device revoke front-door-1
```

On a retired phone, long-press the app title and confirm removal. Revoke the database device as well. Provisioning the same device ID again rotates its key and reactivates it.

## 3. Start the scanner

```powershell
cd C:\Users\Admin\ypgym\scanner-mobile
Copy-Item .env.example .env
# Edit only EXPO_PUBLIC_API_URL; never add the device key.
npm ci
npx expo start --lan
```

After a backend host/Wi-Fi change, update the API URL by removing/reprovisioning the device, restart Expo, and scan a fresh member QR. Rotating QR tokens cannot be replayed or queued offline.

## 4. Safe verification

- Scanner credential check: use the first-run Verify & Save action. The API returns only device ID, display name, and active status.
- Occupancy: sign into web/mobile and view crowdedness, or call the authenticated `/attendance/crowdedness` endpoint. PostgreSQL active sessions remain authoritative.
- Realtime: open a member dashboard and authorized `/admin/attendance` page, perform a scan, and confirm both refetch without manual refresh. The WebSocket sends invalidations only; clients refetch REST.
- Simulator compatibility: `cd iot-simulator; python -m app.main --scenario valid --token "<fresh QR>"`.

## 5. Android development build without publishing

`npm run export:android` validates the JavaScript bundle but does not create an installable APK. To build and install a local development client on an owner-controlled Android phone:

1. Install Android Studio, its Android SDK/platform tools, and a compatible JDK. Enable USB debugging on the phone and confirm `adb devices` lists it.
2. Replace the placeholder Android package and URL scheme in `scanner-mobile/app.json` with owner-approved identifiers before distributing any build.
3. Keep the backend URL reachable from the phone and run:

```powershell
cd C:\Users\Admin\ypgym\scanner-mobile
npm ci
npx expo run:android --device
```

This creates/uses a local native development project and installs it on the selected device; it does not publish to Google Play. Do not commit generated native signing files, keystores, or production device credentials. A signed release AAB and store submission remain a separate owner-approved release task.

## 6. Two-phone acceptance

1. Device A: sign into the existing member app with an eligible verified member and open My QR.
2. Device B: provision the dedicated scanner and select Check in.
3. Scan Device A. Confirm Device B shows the server-derived name, membership status, time, and increased occupancy.
4. Confirm the foreground member dashboard/attendance and authorized web attendance screen update without manual refresh.
5. Retry the same/current QR and confirm duplicate/already-active guidance.
6. Obtain a fresh QR, select Check out, scan, and confirm reduced occupancy and client refresh.
7. Repeat with expired, superseded, and inactive-member cases.
8. Disconnect Device B's network. Confirm it states that no attendance was recorded and keeps no queue. Reconnect and scan a fresh QR.

Record actual scan-response and client-refresh timing; two seconds on a local network is a target, not a guarantee.

## Troubleshooting

| Symptom | Check |
|---|---|
| Camera unavailable | Grant camera permission in phone settings, foreground the app, then retry. |
| API unreachable | Use the PC's LAN IP, private-network firewall permission, and non-isolated Wi-Fi. Do not use PC `localhost` on the phone. |
| `INVALID_DEVICE` | Confirm the exact device ID/key, active database device, and whether the key was rotated/revoked. |
| Expired/superseded QR | Ask the member to keep My QR open and scan the newly refreshed code. |
| `QR_STATE_UNAVAILABLE` / `SCAN_STATE_UNAVAILABLE` | Confirm Redis is healthy, then retry only with a newly displayed QR; no earlier scan is queued. |
| Generic backend failure | Confirm `/api/v1/health`, retain the displayed request ID for safe log correlation, and do not retry a captured QR blindly. |
| HTTPS/certificate failure | Use a trusted certificate and `https://`; self-signed certificates are normally rejected by phones. |
| Stale client screen | Foreground/reload once, verify the WebSocket endpoint and Redis, then confirm REST still returns current data. |
| Wi-Fi changed | Reprovision with the reachable API URL and restart Expo; never reuse a captured QR. |

Production follow-up: replace manual key entry with an expiring, single-use, owner-authorized provisioning exchange. This task deliberately does not pretend the development form is production enrollment.

Automated and local integration results, the outstanding physical-device gate, and pre-distribution owner actions are recorded in [`docs/release/scanner-mobile-evidence.md`](../release/scanner-mobile-evidence.md).
