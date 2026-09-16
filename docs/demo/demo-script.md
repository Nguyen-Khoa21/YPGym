# Examiner demo script

## Start an isolated local demo

```powershell
cd C:\Users\Admin\ypgym
docker compose -p ypgym-demo -f compose.demo.yml config --quiet
docker compose -p ypgym-demo -f compose.demo.yml up -d --build
docker compose -p ypgym-demo -f compose.demo.yml ps
Invoke-RestMethod http://localhost:58001/api/v1/health/dependencies
```

Open web `http://localhost:55174`; Swagger `http://localhost:58001/docs`. The API migrates and runs `python -m app.db.seed --demo` before starting; worker/beat/web wait for API health. This standalone file has separate project volumes, no fixed container names, and no published PostgreSQL/Redis ports. Never merge it with the normal application Compose file or use the normal project name/volumes.

All seeded accounts use local-only password `YPGymDemo123!`. Existing passwords are not overwritten. `--demo` refuses normal `ypgym` storage and production environments.

| Email | Role / tier | Initial scenario |
|---|---|---|
| `admin@ypgym.dev` | Admin | CRM, billing, classes and audited actions |
| `manager@ypgym.dev` | Manager | Approvals, trainers, analytics, audit and configuration |
| `staff@ypgym.dev` | Staff | Attendance; manager analytics denied |
| `pt@ypgym.dev` | PT | Protected trainer landing and coach profile |
| `member@ypgym.dev` | Member / VIP | Active annual membership, invoice and Mobility booking |
| `advance@ypgym.dev` | Member / Advance | Active; holds the only Capacity One place |
| `normal@ypgym.dev` | Member / Normal | Active; Capacity One waitlist position 1 |
| `frozen@ypgym.dev` | Member / Advance | Frozen now; QR/booking denied |
| `expired@ypgym.dev` | Member / Normal | Expired yesterday; QR/booking denied; renewal available |
| `revoked@ypgym.dev` | Member / Normal | Revoked with synthetic reason/admin; QR/booking/self-renewal denied |
| `cancelled@ypgym.dev` | Member / Normal | Cancelled; QR/booking denied |
| `newmember@ypgym.dev` | Member / Normal | Verified without membership; purchase demonstration |

Data also includes six VND plans, payment/invoice, preferences/notifications, a trainer, three future classes, two bookings, a waitlist, a live broadcast and 21 additional closed visits across seven UTC days plus the original visit. Re-seeding retains IDs/invoice snapshots, refreshes synthetic membership/history dates, rolls elapsed base class dates forward and retains completed booking/waitlist decisions. It does not reset an already performed demo; reset only the isolated project to replay from initial records.

## Connected HTTP rehearsal

Run once on fresh demo records:

```powershell
docker compose -p ypgym-demo -f compose.demo.yml exec -T backend-api python -m scripts.demo_smoke --base-url http://localhost:8000/api/v1
docker compose -p ypgym-demo -f compose.demo.yml exec -T celery-worker celery -A app.workers.celery_app inspect ping --timeout 5
```

The smoke uses actual HTTP/JWT endpoints for purchase/renewal/idempotency, invoice PDF, current QR/scanner/duplicate/checkout, occupancy, booking/waitlist/promotion, CRM revocation/audit, exports, manager cache and staff/PT denials. It intentionally changes synthetic records and refuses normal storage. It does not prove browser/native rendering or human UAT. Restore fresh demo resources before presenting the initial interactive sequence.

## Interactive examiner sequence

1. **Login:** At `/login` sign in as the VIP member. `/app/dashboard` shows Maya Member, Active membership, future Mobility booking, broadcast and notification. Member access to operations routes is denied.
2. **Purchase/renewal:** As New Member open `/memberships`, select 1 Month and confirm the explicitly simulated payment. Expect 720,000 VND, activation and backend-confirmed success. As the original member, renewal extends from current expiry. Replaying the same idempotency key retains one payment/invoice.
3. **Invoice:** At `/app/billing` download the new PDF and original annual invoice: VND amounts, immutable coverage snapshots, original discounted amount 5,508,000 VND. Another member cannot download it.
4. **QR:** At `/app/qr` show the currently server-issued token/countdown. Refresh rotates it; the old code is superseded. Frozen/expired/revoked/cancelled/no-membership accounts show guidance without a valid code.
5. **Scanner/occupancy:** Copy a current synthetic member QR. From `iot-simulator/` run the commands below. Duplicate scenario checks in once, then returns 409 without double counting. Dashboard/manager crowdedness increases by one; rotate before checkout and confirm it returns to the prior count. Never save token material in documentation/logs. Use the HTTP smoke as a fallback when a token expires while copying.

   ```powershell
   python -m app.main --base-url http://localhost:58001/api/v1 --api-key local-demo-scanner-key --scenario duplicate --token "<current QR token>"
   # Refresh QR first, then use its new token:
   python -m app.main --base-url http://localhost:58001/api/v1 --api-key local-demo-scanner-key --action check-out --token "<new current QR token>"
   ```

6. **Booking/waitlist:** `/app/classes` shows Strength with spare capacity and Capacity One full. Book Strength and join Capacity One as the member (position 2). As Advance cancel its Capacity One booking at `/app/bookings`; Normal is promoted first, with consistent dashboard/bookings and preference-aware notifications after refresh. The member remains waiting. Fixture dates are several days beyond the inclusive 12-hour cancellation cutoff.
7. **CRM/audit:** As Admin inspect Advance at `/admin/members`, revoke with a reason of at least ten characters, then find the single `membership.revoked` entry at `/admin/audit`. The target loses access; Manager can read audit but cannot export CRM. Staff can operate `/admin/attendance`, not manager analytics.
8. **Analytics/classes/PT:** Manager `/admin/attendance` has real seven-day UTC visits and persisted summary with 60-second cache. Admin `/admin/classes` can add a future non-overlapping trainer class with positive capacity, verify member visibility, and cancel with a reason. Manager `/admin/pt-assignments` maintains trainers; deactivation requires future reassignment. PT uses `/pt/dashboard`; advanced PT business functions remain outside scope.
9. **Mobile same backend:** In the ignored `mobile/.env` use API `http://10.0.2.2:58001/api/v1` for an emulator, `http://localhost:58001/api/v1` for Expo web, or `http://<computer LAN IPv4>:58001/api/v1` for a phone on the same network. From `mobile/` restart Metro with `npx expo start --go --port 8082`. Show authenticated Dashboard, QR, Classes, renewal selection/success and Profile; refresh to see web/scanner changes. Web preview is separate from native evidence. Restore normal API port 8001 afterward.
10. **Failure states:** Check empty search, field validation, role denial, logout/back, expiry and QR hiding on background/connectivity failure. Pause only the demo backend to test retry/error UI, then restore it; preserve normal services. Record viewports/device/screenshots; partial keyboard checks do not establish full accessibility conformance.

## Private development mail and reset

Registration requires its one-time verification message. Demo mail is private inside the demo storage volume at `/app/storage/mail/new/`; it is not external SMTP delivery and links are not logged. Copy an individual message to an ignored local folder for inspection if needed; never include the outbox in archives/screenshots. Seeded accounts are verified, so a missing mail viewer does not block the main sequence. Account integration tests separately exercise registration/verification/reset.

```powershell
cd C:\Users\Admin\ypgym
docker compose -p ypgym-demo -f compose.demo.yml down
# Delete ONLY synthetic demo volumes when replay from empty storage is needed:
docker compose -p ypgym-demo -f compose.demo.yml down --volumes
docker compose -p ypgym-demo -f compose.demo.yml up -d --build
```

Never apply `--volumes` to the normal application project. This runbook is software rehearsal, not human evaluation or final submission readiness.

Evidence indexes belong under `docs/design/evidence/`; the route map and release tracker must be updated with the actual date, viewport/device, and observed result.
