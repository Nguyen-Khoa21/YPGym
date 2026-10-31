# YPGym QR Attendance Scanner Run Guide

This guide runs the dedicated Expo attendance scanner in `scanner-mobile/`. The easiest test setup uses:

- the YPGym web app on the computer to display a member QR code; and
- one physical phone running the scanner in Expo Go.

The scanner phone must be able to reach the YPGym API on the computer. Do not use `localhost` as the API host on a physical phone.

## Prerequisites

- Docker Desktop is running.
- Node.js and npm are installed.
- Expo Go compatible with Expo SDK 58 is installed on the scanner phone.
- The computer and phone are on the same private network and can communicate with each other.

Guest or coffee-shop Wi-Fi can block communication between devices even when both devices show the same Wi-Fi name. If that happens, use a private router or a personal hotspot.

## 1. Start YPGym

Open PowerShell and run:

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app up -d --build
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api python -m app.db.seed
```

Check the API on the computer:

```text
http://localhost:8001/api/v1/health
```

Check the web app:

```text
http://localhost:5174
```

## 2. Find the computer's LAN IP address

Run:

```powershell
ipconfig
```

Find the `IPv4 Address` under the active Wi-Fi or Ethernet adapter. For example:

```text
192.168.1.100
```

On the phone, open this address in its browser, replacing the example IP:

```text
http://192.168.1.100:8001/api/v1/health
```

Continue only if the health response opens on the phone. The scanner API URL will be the same address with `/api/v1` at the end:

```text
http://192.168.1.100:8001/api/v1
```

If the health page does not open, check that:

- the phone and computer are on a network that permits device-to-device traffic;
- Docker services are running;
- Windows Firewall permits inbound TCP port `8001` on the trusted private network; and
- the IP address belongs to the active network adapter.

## 3. Provision a scanner device

Choose a unique device ID, such as `front-door-1`, and a private API key containing at least 24 characters. Run:

```powershell
cd C:\Users\Admin\ypgym
docker compose exec backend-api python -m app.cli.scanner_device provision front-door-1 "Front door scanner"
```

When prompted, type the API key twice. PowerShell will not display the characters while you type. Save the key temporarily in a secure password manager because the backend will not display it later.

Do not add the device key to `.env`, source control, screenshots, or chat. Provisioning the same device ID again rotates its key and invalidates the previous key.

## 4. Configure the scanner app

Run:

```powershell
cd C:\Users\Admin\ypgym\scanner-mobile
Copy-Item .env.example .env
notepad .env
```

Set the API URL to the computer's LAN IP. Keep `/api/v1` in the URL:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.100:8001/api/v1
EXPO_PUBLIC_GYM_TIMEZONE=Asia/Ho_Chi_Minh
```

Replace `192.168.1.100` with the actual computer IP, save the file, and close Notepad. Never put the scanner device key in this file.

## 5. Start the Expo scanner

From `C:\Users\Admin\ypgym\scanner-mobile`, run:

```powershell
npm ci
npx expo start --lan
```

Then:

1. Open Expo Go on the scanner phone.
2. Scan the QR code shown by Expo in PowerShell or the Expo browser page.
3. Grant camera permission when requested.
4. Complete the scanner provisioning form:
   - **API URL:** `http://<computer-ip>:8001/api/v1`
   - **Device ID:** `front-door-1`
   - **Device key:** the private key entered in step 3
   - **Mode:** `both`
5. Select **Verify & Save**.

The scanner verifies the device with the backend before storing its credentials in the phone's secure storage.

## 6. Display a member QR code

On the computer, open:

```text
http://localhost:5174/login
```

For the seeded development account, sign in with:

```text
Email: member@ypgym.dev
Password: YPGymDemo123!
```

Open **My QR Code**, or go directly to:

```text
http://localhost:5174/app/qr
```

Keep the page open so the rotating QR code remains current.

You can alternatively display the QR code in the separate YPGym member mobile app on a second phone.

## 7. Test check-in and check-out

### Check in

1. Select **Check in** in the scanner app.
2. Point the scanner phone at the current member QR code on the computer screen.
3. Confirm that the result shows the member name, membership status, scan time, attendance status, occupancy, and crowdedness.
4. Open the member attendance page or the administrator attendance page and confirm the new visit appears.

### Check out

1. Wait for the member page to display a fresh QR code.
2. Select **Check out** in the scanner app.
3. Scan the fresh QR code.
4. Confirm the attendance session closes and occupancy decreases.

Do not reuse a copied or expired QR token. QR codes rotate and are protected against expiry, supersession, and replay.

## Everyday restart

If YPGym is already installed and provisioned, start the services and scanner with:

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app up -d

cd C:\Users\Admin\ypgym\scanner-mobile
npx expo start --lan
```

If the computer's IP address or Wi-Fi network changes, update `scanner-mobile/.env`, restart Expo, and enter the reachable API URL in the scanner provisioning form again.

## Stop the applications

Press `Ctrl+C` in the Expo terminal, then run:

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app down
```

## Revoke or reset a scanner

Revoke the device in the backend:

```powershell
cd C:\Users\Admin\ypgym
docker compose exec -T backend-api python -m app.cli.scanner_device revoke front-door-1
```

To remove saved credentials from the phone, press and hold the **YPGym Scanner** title for about two seconds and confirm removal.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Expo QR code does not open | Use `npx expo start --lan`, confirm the phone can reach the computer, and avoid isolated guest Wi-Fi. |
| API cannot be reached | Open `http://<computer-ip>:8001/api/v1/health` on the phone. Do not use `localhost` or the default gateway address. |
| `INVALID_DEVICE` | Check the exact device ID and key. Reprovision if the device was revoked or its key was rotated. |
| QR token is invalid or expired | Keep the member QR page open and scan the newly refreshed QR code. Do not type angle brackets around a token. |
| Duplicate/already checked in | The member already has an active attendance session. Switch to **Check out** and scan a fresh QR. |
| Camera is unavailable | Grant Expo Go camera permission in the phone settings and reopen the scanner. |
| Scan reports a network failure | No attendance was recorded. Reconnect and scan a newly displayed QR; the app intentionally keeps no offline queue. |
| Client screen looks stale | Bring the page/app to the foreground or reload once, then verify Redis and the realtime WebSocket service are running. |

For provisioning security, native Android builds, two-phone acceptance testing, and production limitations, see [`docs/runbooks/scanner-mobile.md`](docs/runbooks/scanner-mobile.md).
