# Days 21-38 Demo Script

## Prepare

```powershell
docker compose --profile app up -d
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api python -m app.db.seed
docker compose ps
```

All demo accounts use `YPGymDemo123!`.

## Member journey (`member@ypgym.dev`)

1. Open `/app/dashboard`; confirm the active welcome broadcast and live crowdedness card.
2. Open `/app/qr`; confirm a rendered QR, status, countdown, refresh behavior, capacity, and recent attendance.
3. Open `/app/attendance`; confirm seeded and scanner-created sessions with event/source detail.
4. Open `/app/membership-requests`; submit a future freeze or cancellation request with a valid reason.
5. Open notification preferences, save supported channels, then return to the paginated inbox and mark the seeded notification read.
6. Open billing history and download the seeded PDF invoice.

## Manager journey (`manager@ypgym.dev`)

1. Open `/admin/approvals`; decide the pending member request with a reason. For cancellation approval, choose refund, account credit, or forfeit.
2. Open `/admin/attendance`; inspect facility KPIs and the complete 7x24 peak-hours grid. Manager cannot access billing/CRM/classes.
3. Create a short active broadcast, confirm member visibility, then deactivate it.
4. Update an operational configuration value within its safe range and confirm it in the audit log.
5. Filter audit by date/action/actor/target/entity.

## Staff journey (`staff@ypgym.dev`)

1. Open `/admin/attendance`; filter by member/status/date.
2. If a session is active, close it with a reason. Repeat closure to demonstrate idempotency.
3. Confirm analytics, approvals, audit, configuration, CRM, billing, and classes are not available.

## Admin journey (`admin@ypgym.dev`)

1. Filter `/admin/members` by member, role, tier, status, and expiry; export the same filter set.
2. Open Maya Member details and inspect profile, membership, representative payment/invoice, attendance, request history, and audit trail.
3. Open `/admin/billing`; combine member/status/date/plan/tier filters and export payments or invoices.
4. Open `/admin/classes`; create a future class, edit capacity/trainer/location, then cancel with confirmation and reason.
5. Confirm class/member/billing operations appear in `/admin/audit`.

## Scanner demo

Copy the current token from My QR and use `docs/api/iot-scanner.md`. Demonstrate valid check-in/out plus invalid, expired, superseded, inactive, duplicate, and unauthorized-device responses. Always close the final active session.

## Explicit non-demo scope

Do not imply that the following are connected: member class booking/waitlist, PT profile/assignment management, real refund settlement/payment gateway, Expo/mobile apps, physical firmware, or AI/personalization.
