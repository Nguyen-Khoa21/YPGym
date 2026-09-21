# YPGym member app

The Expo/React Native app uses the existing YPGym FastAPI backend. It includes member registration, email verification, sign-in and session restoration, membership purchase/renewal and freeze/cancellation requests, a live dashboard and rotating check-in QR, class booking and waitlists, attendance-day history, actionable in-app class reminders, profile editing, preferences and invoices. The operations workspace remains in the web app.

## Run in Expo web on this computer

Use `http://localhost:8001/api/v1` for Expo web. The Android emulator address `10.0.2.2` is only for an Android emulator.

```powershell
cd C:\Users\Admin\ypgym\mobile
(Get-Content .env.example) -replace '^EXPO_PUBLIC_API_URL=.*$', 'EXPO_PUBLIC_API_URL=http://localhost:8001/api/v1' | Set-Content .env
npm ci
npx expo start --web
```

Restart Expo after changing `.env`. The API allows the local Expo web origins on ports 8081, 8082, and 19006.

## Run on an Android emulator (Windows PowerShell)

Install Node.js 22.13 or newer and Android Studio with an Android SDK emulator. Create and start an Android Virtual Device in Android Studio. From the repository root:

```powershell
docker compose --profile app up -d --build
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api python -m app.db.seed
Invoke-RestMethod http://localhost:8001/api/v1/health

cd mobile
Copy-Item .env.example .env
npm ci
npm run android
```

The `.env.example` address `http://10.0.2.2:8001/api/v1` reaches the host API from the standard Android emulator. Expo starts Metro, installs a compatible Expo Go if needed, and opens the app. Check the Metro listener and `/status` before restarting it. September 16 testing found `--localhost` bound only IPv6 while Expo Go used IPv4; LAN binding plus task-specific ADB reverse forwarding resolved the update-download failure. This is separate from the API URL setting.

Sign in as `member@ypgym.dev` with the local seed password `YPGymDemo123!`. The app rejects operations roles. The gym API health line on the sign-in screen should say **Gym API online** before sign-in.

## Run on a physical phone

Install the SDK 57 compatible Expo Go on the phone. Put the phone and Windows computer on the same network. In `mobile/.env`, change `EXPO_PUBLIC_API_URL` to `http://<your-computer-LAN-IPv4>:8001/api/v1`; find that IPv4 with `ipconfig`. Confirm the phone can reach the API address and that Windows Firewall allows the backend port. Then run `npm start` from `mobile/` and scan its QR code in Expo Go. Restart Metro after editing `.env`, because Expo embeds public variables in the JavaScript bundle. A phone cannot use the Android emulator's `10.0.2.2` address.

On Windows, Android Studio provides the local native emulator. An iOS simulator requires macOS; a compatible Expo Go on a real iPhone can connect over the local network.

## Verify the app

From `mobile/`:

```powershell
npm run typecheck
npm run lint
npm test
npx expo-doctor
npx expo export --platform android
```

After signing in, check Dashboard, Check-in, Classes, and Profile tabs. A valid active membership receives a short-lived QR token from the server; it disappears when expired or the app moves to the background. Booking and waitlist actions require an eligible membership. The renewal flow clearly confirms a **simulated** payment and displays success only after the new invoice appears in the account. No real payment method is charged.

New members can use **Create a member account** and follow the one-time `ypgym://verify-email` link written to the development Maildir alongside the web link. Profile → Membership Requests submits real freeze/cancellation requests and shows their staff-reviewed status. Booked-class reminders are stored by the backend, respect Notification Preferences, and open the matching booking from the inbox. The manager-configured lead time defaults to 120 minutes. Device push is not configured; reminders appear in the persistent in-app inbox. Dates, class times and distinct visit days use `GYM_TIMEZONE` / `EXPO_PUBLIC_GYM_TIMEZONE`, both defaulting to `Asia/Ho_Chi_Minh`; keep these deployment values aligned.

Logout removes the native SecureStore token (or both browser storage fallbacks), clears member-specific query data and replaces the navigation stack with the login screen. The API currently has no logout/token-revocation endpoint, so server-side revocation is not claimed; access tokens still expire according to backend configuration. Expired tokens are removed when session restoration or an authenticated request receives HTTP 401. Nested pages use route-aware Back arrows and fall back to a safe member screen when opened directly.

Dashboard, Profile, Check-in and renewal screens refetch the server membership state when mounted and after the app returns to the foreground. A confirmed mock purchase invalidates and refetches dashboard, profile, QR, invoice/billing, plan and membership query groups before showing the server-backed success receipt. Cancelled, expired, frozen and revoked states remain visibly distinct from the member's account tier and cannot display an eligible QR.

The member app uses the shared white-and-green workout visual system documented in `../docs/design/workout-visual-system.md`. Semantic colors, spacing, radii and shadows live in `src/lib/theme.ts`; shared controls and loading, empty, error and form-validation states live in `src/components/ui.tsx`. The content container adapts from phone through tablet and Expo web widths while keeping the Dashboard, Check-in, Classes and Profile tabs in their established order.

The web portal still runs at `http://localhost:5174`; OpenAPI is at `http://localhost:8001/docs`. The current development handoff is `../docs/HANDOFF.md`.

For the isolated Day58 demo use API port `58001` and the synthetic accounts in `../docs/demo/demo-script.md`. Start the separate `compose.demo.yml` stack; use its records for policy demonstrations.

The September 16 Android rehearsal kept the existing localhost API `.env` and used the following forwarding instead of editing it. These commands apply only to the named emulator; physical phones use the LAN instructions above. Run Metro from `mobile/` and keep it running:

```powershell
$ypgymAdb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
& $ypgymAdb -s emulator-5554 reverse tcp:8001 tcp:58001
& $ypgymAdb -s emulator-5554 reverse tcp:8082 tcp:8082
npx expo start --go --lan --port 8082
```

In a second PowerShell window open Expo Go with `& $ypgymAdb -s emulator-5554 shell am start -a android.intent.action.VIEW -d exp://127.0.0.1:8082 host.exp.exponent` (define the same `$ypgymAdb` there). After this demo remove only its two mappings with `reverse --remove tcp:8001` and `reverse --remove tcp:8082`. Device API port 8001 reaches the isolated host demo 58001 during this test; the ordinary host API 8001 is unaffected. Native evidence and remaining acceptance cases are indexed in `../docs/design/evidence/day-47-mobile/README.md`.
