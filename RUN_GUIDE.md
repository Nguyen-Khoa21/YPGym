# YPGym: run, log in and build

Updated October 12, 2026. These instructions use **Windows PowerShell** and your checkout at `C:\Users\Admin\ypgym`. Run one section at a time. Keep the backend running while using either client.

## 1. What you need

- Docker Desktop installed and running with Linux containers.
- Node.js and npm for host web builds and Expo. This checkout was checked with Node **22.20.0** and npm **11.12.1**.
- Expo Go compatible with this project's **Expo SDK 57** for a phone or emulator.
- Android Studio with a started Android Virtual Device for emulator testing. Native Android compilation also requires the configured Android SDK and Java.

Check your terminal:

```powershell
cd C:\Users\Admin\ypgym
docker --version
docker info
node --version
npm --version
```

You do not need host Python to start the normal application; backend commands run inside Docker. YPGym login credentials below are separate from any Expo account.

## 2. Start the backend and web portal

In **Terminal 1**, run:

```powershell
cd C:\Users\Admin\ypgym

# Create optional local configuration only if it is missing.
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (-not (Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }

docker compose --env-file backend/.env config --quiet
docker compose --env-file backend/.env --profile app up -d --build
docker compose --env-file backend/.env exec -T backend-api alembic upgrade head
docker compose --env-file backend/.env exec -T backend-api python -m app.db.seed
docker compose --env-file backend/.env ps
Invoke-RestMethod http://localhost:8001/api/v1/health/dependencies
```

Run each command only after the previous command finishes, and stop if a command prints an error. The seed is repeatable and preserves existing passwords/history. The dependency probe should report `database: ok` and `redis: ok`.

The `--env-file backend/.env` option is required for this checkout. It loads the configured SMTP, Google OAuth and Facebook OAuth credentials into the recreated services. Starting with only `docker compose --profile app up ...` can leave those integrations disabled because Compose otherwise reads the repository-root `.env`.

When testing live SMTP, register with a real mailbox you control. Addresses such as `welcome@example.com` are test-only; `example.com` intentionally has no receiving mail server, so Gmail will accept the outbound SMTP message and then return an **Address not found** bounce.

This starts PostgreSQL, Redis, FastAPI, Celery worker/beat and the Vite web development server. `--build` builds their Docker images; the separate web production build is in section 4.

| What to open | Default address |
|---|---|
| Web login | [http://localhost:5174/login](http://localhost:5174/login) |
| Web homepage | [http://localhost:5174](http://localhost:5174) |
| API health | [http://localhost:8001/api/v1/health](http://localhost:8001/api/v1/health) |
| API/database/cache health | [http://localhost:8001/api/v1/health/dependencies](http://localhost:8001/api/v1/health/dependencies) |
| Swagger API documentation | [http://localhost:8001/docs](http://localhost:8001/docs) |
| PostgreSQL host port | `127.0.0.1:5433` |
| Redis host port | `127.0.0.1:6380` |

Addresses assume the existing Compose default ports. If you intentionally changed root environment overrides, use the published ports shown by `docker compose ps`.

On later days, start the same services with:

```powershell
cd C:\Users\Admin\ypgym
docker compose --env-file backend/.env --profile app up -d
```

Run migrations after pulling migration changes, and use `up -d --build` after Docker/dependency changes.

## 3. Web login credentials for every role

These are the public **local development seed accounts**, not production credentials. Their default password is **`YPGymDemo123!`**. All five default logins below returned HTTP 200 on September 17, 2026.

| Role | Email | Password | Landing page / main access |
|---|---|---|---|
| Member | `member@ypgym.dev` | `YPGymDemo123!` | `/app/dashboard`: QR, classes, bookings, profile, billing, notifications |
| Admin | `admin@ypgym.dev` | `YPGymDemo123!` | `/admin`: CRM, billing/exports, classes, approvals, trainers, analytics, audit, settings |
| Manager | `manager@ypgym.dev` | `YPGymDemo123!` | `/admin`: attendance/analytics, approvals, trainers, broadcasts, audit, settings |
| Staff | `staff@ypgym.dev` | `YPGymDemo123!` | `/admin`: attendance desk/history and manual closure |
| Personal trainer | `pt@ypgym.dev` | `YPGymDemo123!` | `/pt/dashboard`: own linked profile and next-three assigned classes |

Open the login URL, enter one account, and sign out before testing another role. A manager cannot use admin-only CRM/billing/class scheduling, and staff cannot use manager analytics. PT access is a lightweight read-only workspace.

If an existing account's password was changed, use that changed password. The seed does not reset it. `DEVELOPMENT_SEED_PASSWORD` can also change the password used for newly created normal-stack accounts. Do not reset your database just to restore a login.

### Test an independently paid class

1. Sign in as `admin@ypgym.dev`, open `/admin/classes`, and create or edit a future session with a positive VND price.
2. Sign out, register or use any verified member account, then open `/app/classes`. An active gym membership is not required.
3. Check the session price, time, remaining seats, and refund terms. Select **Book & pay** once; YPGym holds the seat for the configured 15-minute VNPay transaction lifetime.
4. Complete VNPay sandbox checkout. The return page waits for the authoritative IPN; the browser redirect itself does not confirm the seat.
5. Check `/app/bookings` for booking/payment/refund state and `/app/billing` for the class receipt. As admin, use `/admin/billing` and filter **Class bookings** to inspect revenue, pending holds, and refund exceptions.

Member cancellation is allowed before the class starts. A paid cancellation is labelled **Refund review** because YPGym does not claim an automatic VNPay refund. After completing the provider-side refund or other resolution, an admin can select **Mark resolved** in `/admin/billing`, enter a reason, and create the audit record. Cancelling the class itself flags all settled class purchases for the same review and cancels active holds/waitlists.

For a real sandbox callback, keep the Cloudflare tunnel running and update both the configured VNPay merchant IPN URL and `VNPAY_RETURN_URL` to the tunnel's current HTTPS hostname. Quick Tunnel hostnames change after restart. The final route contract and migration behavior are in `docs/api/paid-class-bookings.md`.

### Test an attendance-based membership renewal

1. Sign in with a verified member whose current membership is active or expiring soon.
2. Open `/memberships`, choose a plan, and continue to its checkout screen. Expo members use **Profile → Membership plan → Renew**.
3. The screen shows distinct QR check-in days for the previous complete gym-local month, that month's actual day count, the percentage, plan discount, attendance discount and final amount.
4. At 80% or more, the server offers 10% for the next renewal. It applies whichever is higher: the plan discount or 10%. The two discounts do not stack.
5. Complete VNPay sandbox checkout. A failed/cancelled/expired payment releases the benefit; the first successful renewal consumes it. Verify the stored breakdown on the payment result and `/app/billing` or the Expo invoices screen.

Only `iot-simulator` QR check-ins count. Staff/manual attendance entries and repeated scans on the same local date do not increase the numerator. See `docs/api/attendance-renewal-benefit.md` for the exact contract and automated boundary/concurrency coverage.

## 4. Web development and production build on the host

The Docker web portal already works after section 2. Use this section when you want the web dev server/build in your own terminal. Stop only the Docker frontend to free port 5174; keep the API/database/cache running.

### Host development server

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app stop frontend-web

cd C:\Users\Admin\ypgym\frontend
npm ci
$env:VITE_API_BASE_URL = 'http://localhost:8001/api/v1'
npm run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

Keep this terminal open. Visit [http://localhost:5174/login](http://localhost:5174/login). Port 5174 matches the backend's configured web origin.

### Build and preview production assets

Stop the host dev server with **Ctrl+C**, then run:

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app stop frontend-web

cd C:\Users\Admin\ypgym\frontend
npm ci
$env:VITE_API_BASE_URL = 'http://localhost:8001/api/v1'
npm run lint
npm run build
npm run preview -- --host 127.0.0.1 --port 5174 --strictPort
```

`npm run build` performs TypeScript compilation and writes assets to `frontend/dist/`. Preview serves those assets at the same web URL while your backend stays running. The API URL is embedded at build time; changing it requires rebuilding. Preview is for local review, not public deployment.

To rebuild everything in Docker instead:

```powershell
cd C:\Users\Admin\ypgym
docker compose --env-file backend/.env --profile app up -d --build
```

If a changed frontend lockfile is not reflected in the mounted container dependencies:

```powershell
docker compose exec -T frontend-web npm ci
docker compose restart frontend-web
```

To return from a host dev/preview server to Docker, press Ctrl+C in that host terminal, then:

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app start frontend-web
```

## 5. Install the mobile project's dependencies

Leave section 2's backend running. In a **new PowerShell terminal**:

```powershell
cd C:\Users\Admin\ypgym\mobile
npm ci
```

Run `npm ci` again after the mobile lockfile changes. Choose **one** launch method below. The commands set `EXPO_PUBLIC_API_URL` for that terminal and take precedence over an existing `.env`; they do not overwrite your local file. After changing the address, stop Expo with Ctrl+C and restart it.

| Where the mobile client runs | API base URL for the normal stack |
|---|---|
| Expo web on this computer | `http://localhost:8001/api/v1` |
| Standard Android Studio emulator | `http://10.0.2.2:8001/api/v1` |
| Physical phone on the same network | `http://YOUR_COMPUTER_LAN_IP:8001/api/v1` |

**Mobile member login:** `member@ypgym.dev` / `YPGymDemo123!`. The Expo app accepts members; use the web portal for admin, manager, staff and PT accounts. Its login health line should show **Gym API online** before you sign in.

### A. Run on your phone using Expo Go

1. Put the computer and phone on the same Wi-Fi/LAN. Avoid guest-network isolation.
2. Install an SDK57-compatible Expo Go.
3. Find the computer's active Wi-Fi/Ethernet **IPv4** with `ipconfig`; avoid VPN/virtual-adapter addresses.

```powershell
cd C:\Users\Admin\ypgym\mobile
ipconfig
$ypgymLanIp = Read-Host 'Enter the computer Wi-Fi/Ethernet IPv4 shown above'
$env:EXPO_PUBLIC_API_URL = "http://${ypgymLanIp}:8001/api/v1"
npx expo start --go --lan --port 8081 --clear
```

Keep the terminal open. First open `http://YOUR_COMPUTER_LAN_IP:8001/api/v1/health` in the phone browser; it should return the API health response. Then scan the **Expo terminal's QR** using Expo Go on Android or the Camera app on iPhone. This launch QR is separate from the member's gym check-in QR inside YPGym.

If the phone cannot connect, allow Docker/backend TCP8001 and Node/Expo TCP8081 through Windows Firewall for the trusted local network. Keep firewall protection enabled. `localhost` points to the phone itself; `10.0.2.2` is for the emulator. Physical-phone/iOS behavior is not yet part of the verified emulator evidence.

### B. Run in an Android Studio emulator

Start an Android Virtual Device from Android Studio's Device Manager, then:

```powershell
cd C:\Users\Admin\ypgym\mobile
$env:EXPO_PUBLIC_API_URL = 'http://10.0.2.2:8001/api/v1'
npx expo start --go --lan --android --port 8081 --clear
```

Alternatively start Expo without `--android` and press **a** to open it. Keep Metro running.

### C. Run the mobile UI in a web browser

```powershell
cd C:\Users\Admin\ypgym\mobile
$env:EXPO_PUBLIC_API_URL = 'http://localhost:8001/api/v1'
npx expo start --web --port 8081 --clear
```

Open [http://localhost:8081](http://localhost:8081) if the browser does not open. This previews the mobile project in a browser; the separate React web portal stays at port5174. The API explicitly allows local Expo web origins on ports8081/8082/19006.

If you previously saw **“The API cannot be reached”**, use this localhost API address for Expo web, restart Expo, and check the API health URL. An Android-emulator API address will not work in your computer's browser.

## 6. Check and build the mobile app

From `mobile/`, first choose an API URL from section 5. It will be embedded in the exported/built client.

### Type checking, lint, tests and Android bundle export

```powershell
cd C:\Users\Admin\ypgym\mobile
npm run typecheck
npm run lint
npm test
npx expo-doctor
npx expo export --platform android
```

The export writes JavaScript/assets to `mobile/dist/`; it does **not** create an installable APK. You can use Expo Go without compiling your own native application. See the [official Expo CLI export/build reference](https://docs.expo.dev/more/expo-cli/).

### Optional: compile and run your own Android app

With Android Studio, SDK and Java configured, start an emulator or connect a USB-debugging Android phone. Stop an existing Expo process before starting this build:

```powershell
cd C:\Users\Admin\ypgym\mobile
$env:EXPO_PUBLIC_API_URL = 'http://10.0.2.2:8001/api/v1'
npx expo run:android --variant debug --port 8081
```

For a physical device, set the LAN API address from section5 instead. This generates the ignored native Android folder if needed, compiles a debug app and runs it with Metro. Follow any first-time Android application-ID prompt; `app.json` currently has no explicit Android package identifier. The default Gradle debug APK is normally under `mobile/android/app/build/outputs/apk/debug/`.

To test a release variant locally:

```powershell
npx expo run:android --variant release
```

Local native compilation was not rerun when writing this guide. Release signing/store distribution still needs separate configuration; this command does not provide Play Store submission signing. [Expo's local compilation documentation](https://docs.expo.dev/more/expo-cli/#compiling) covers the toolchain and variants.

Native iOS compilation/simulation needs **macOS and Xcode**. On a configured Mac checkout, install mobile dependencies, set a reachable backend URL, and use `npx expo run:ios`; this cannot run locally on your Windows computer. A compatible physical iPhone uses the Expo Go/LAN instructions above. [Expo environment setup](https://docs.expo.dev/get-started/set-up-your-environment/) describes the platform setup.

## 7. Optional isolated demo with additional member accounts

Use this separate stack when you want prepared Active/Frozen/Expired/Revoked/Cancelled and booking/waitlist examples. It does not use the normal database or normal API ports.

```powershell
cd C:\Users\Admin\ypgym
docker compose -p ypgym-demo -f compose.demo.yml config --quiet
docker compose -p ypgym-demo -f compose.demo.yml up -d --build
docker compose -p ypgym-demo -f compose.demo.yml ps
Invoke-RestMethod http://localhost:58001/api/v1/health/dependencies
```

Migrations and `--demo` seeding run automatically before the demo API starts. Open [demo web login](http://localhost:55174/login) or [demo Swagger](http://localhost:58001/docs). The five role accounts from section3 are also seeded here with the same default password. These **seven extra members exist only after isolated demo seeding**:

| Email | Password | Initial demo scenario |
|---|---|---|
| `advance@ypgym.dev` | `YPGymDemo123!` | Advance / Active; holds Capacity One's booking |
| `normal@ypgym.dev` | `YPGymDemo123!` | Normal / Active; first in Capacity One's waitlist |
| `frozen@ypgym.dev` | `YPGymDemo123!` | Advance / Frozen; gym QR denied, paid classes remain available |
| `expired@ypgym.dev` | `YPGymDemo123!` | Normal / Expired; gym QR denied, renewal and paid classes available |
| `revoked@ypgym.dev` | `YPGymDemo123!` | Normal / Revoked; QR/booking/self-renewal denied |
| `cancelled@ypgym.dev` | `YPGymDemo123!` | Normal / Cancelled; gym QR denied, paid classes remain available |
| `newmember@ypgym.dev` | `YPGymDemo123!` | Normal / verified without membership; purchase available |

Re-seeding does not erase completed bookings, purchases or password edits; the scenarios describe initial fixtures. For the full examiner journey see [docs/demo/demo-script.md](docs/demo/demo-script.md).

For **Expo web** on the demo API, stop the normal Expo process and run:

```powershell
cd C:\Users\Admin\ypgym\mobile
$env:EXPO_PUBLIC_API_URL = 'http://localhost:58001/api/v1'
npx expo start --web --port 8081 --clear
```

For an **Android emulator**, use `http://10.0.2.2:58001/api/v1` with the section5B command. The demo API is bound to computer loopback; a physical phone cannot directly reach it over LAN. Use the normal port8001 stack for the phone workflow. Do not merge the demo/test Compose files with the normal Compose file.

## 8. Diagnostics, rebuild checks and stopping

From the repository root:

```powershell
cd C:\Users\Admin\ypgym
docker compose --env-file backend/.env ps
docker compose --env-file backend/.env logs --tail 100 backend-api frontend-web
docker compose --env-file backend/.env exec -T backend-api alembic current
docker compose --env-file backend/.env exec -T backend-api alembic check
Invoke-RestMethod http://localhost:8001/api/v1/health/dependencies
```

Watch API logs live if necessary; Ctrl+C stops following logs:

```powershell
docker compose --env-file backend/.env logs -f --tail 100 backend-api
```

### Error: `No module named 'greenlet'`

The backend declares `sqlalchemy[asyncio]`, which installs the required `greenlet` runtime. If an older cached image was built before that declaration, rebuild the three Python services and then rerun migration and seed:

```powershell
cd C:\Users\Admin\ypgym
docker compose --env-file backend/.env build --no-cache backend-api celery-worker celery-beat
docker compose --env-file backend/.env --profile app up -d backend-api celery-worker celery-beat
docker compose --env-file backend/.env exec -T backend-api alembic upgrade head
docker compose --env-file backend/.env exec -T backend-api python -m app.db.seed
Invoke-RestMethod http://localhost:8001/api/v1/health/dependencies
```

Do not install `greenlet` manually inside a running container; that change disappears when the container is recreated.

To run the full backend tests against disposable PostgreSQL/Redis storage:

```powershell
docker compose -p ypgym-tests -f compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner --attach test-runner
```

This standalone test stack stops after the runner exits. The normal-stack `docker compose exec -T backend-api pytest -q` skips dedicated integration fixtures, so use the standalone test command for full storage coverage.

Stop any host web/Expo terminal with **Ctrl+C**. Stop Docker services while retaining their volumes:

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app stop
```

Stop the optional isolated demo independently:

```powershell
docker compose -p ypgym-demo -f compose.demo.yml stop
```

Do not delete normal volumes to fix a startup or login problem. If a port is already used, stop the previous server for that port; keep Expo web on a configured CORS port or explicitly configure its exact origin.

### Android emulator cannot download the Expo update

If the API is healthy but Expo Go cannot load Metro, use targeted ADB forwarding. This alternative uses **localhost inside the selected emulator**, so both mappings and the following API address are required.

In the mobile terminal:

```powershell
cd C:\Users\Admin\ypgym\mobile
$ypgymAdb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
& $ypgymAdb devices
$ypgymDevice = Read-Host 'Enter the emulator serial listed above, e.g. emulator-5554'
& $ypgymAdb -s $ypgymDevice reverse tcp:8001 tcp:8001
& $ypgymAdb -s $ypgymDevice reverse tcp:8081 tcp:8081
$env:EXPO_PUBLIC_API_URL = 'http://127.0.0.1:8001/api/v1'
npx expo start --go --lan --port 8081 --clear
```

In a second terminal, select the same emulator and open Expo Go:

```powershell
$ypgymAdb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$ypgymDevice = Read-Host 'Enter the same emulator serial'
& $ypgymAdb -s $ypgymDevice shell am start -a android.intent.action.VIEW -d exp://127.0.0.1:8081 host.exp.exponent
```

After this alternative session remove only its mappings:

```powershell
& $ypgymAdb -s $ypgymDevice reverse --remove tcp:8001
& $ypgymAdb -s $ypgymDevice reverse --remove tcp:8081
```

For ordinary emulator networking return to section5B's `10.0.2.2` API URL. Adjust the ADB executable path if you installed the SDK elsewhere.

## 9. What to try after logging in

- **Member/web:** dashboard, valid QR countdown, independently paid class checkout/My Bookings, membership purchase, notifications, profile and invoice download. VNPay completion is confirmed by server IPN.
- **Admin:** member CRM, product-filtered billing/CSV, class pricing, refund-resolution records, trainer assignments and audited actions.
- **Manager:** attendance analytics, approvals, trainers, broadcast, audit and settings.
- **Staff:** attendance history/manual closure; manager/admin actions should be denied.
- **PT:** own profile and upcoming assigned classes.
- **Mobile/member:** Dashboard, QR, Classes, bookings, renewal/success/invoices and Profile; sign out and confirm session cleanup.

An ineligible membership should not show a usable gym QR, but a verified account may still buy a separately priced class. Expired membership renewal follows backend policy. Profile email replacement remains unavailable; name/phone/password actions are supported. Native account-recovery and membership freeze/cancellation requests still use the web portal.

## 10. Guide verification and references

While writing this guide: normal web `/login` returned HTTP200, normal dependency health returned database/Redis `ok`, and all five default normal-stack role logins succeeded without printing access tokens. Normal/demo Compose configuration checks passed. Commands were checked against `frontend/package.json`, `mobile/package.json`, installed Expo CLI help, Compose files and the seed implementation. Host web builds, native compilation, phone launch and isolated-demo reseeding were not executed again for this documentation task.

For implementation and evidence details see [README.md](README.md), [mobile/README.md](mobile/README.md), [docs/demo/demo-script.md](docs/demo/demo-script.md), [role matrix](docs/policies/roles.md), [route-screen map](docs/design/route-screen-map.md) and [current handoff](docs/HANDOFF.md).


## iot simulator demo
cd C:\Users\Admin\ypgym\iot-simulator
python -m app.main --scenario valid --token "<>"
