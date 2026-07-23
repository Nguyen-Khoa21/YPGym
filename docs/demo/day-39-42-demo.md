# Days 39-42 Demo Script

## Prepare

```powershell
docker compose --profile app up -d --build
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api python -m app.db.seed
```

All seeded accounts use `YPGymDemo123!`: `admin@ypgym.dev`, `manager@ypgym.dev`, `staff@ypgym.dev`, `pt@ypgym.dev`, and `member@ypgym.dev`. Create two additional verified member accounts through `/register`, then buy the 1 Month mock plan when demonstrating a multi-member waitlist. Do not reuse real personal information.

## Day 39 trainer profile

1. Sign in as manager or admin and open `/admin/pt-assignments`.
2. Create a trainer with name, specialty, bio, and availability; edit it and confirm the public card at `/app/classes` after assigning it to a future class.
3. Try to deactivate the assigned trainer. Confirm the future-class conflict, reassign or unassign the class at `/admin/classes`, then deactivate successfully.
4. Confirm an ordinary member cannot call trainer management endpoints.

## Days 40-41 booking and waitlist

1. As admin, create a future class with capacity 1.
2. As `member@ypgym.dev`, open `/app/classes`, inspect the trainer/capacity, and book it. A repeat booking must be rejected.
3. As the two additional active members, join the full-class waitlist. Confirm positions 1 then 2 and duplicate rejection.
4. Return to `/app/bookings` as the booked member and cancel before the displayed cutoff.
5. Confirm the first eligible waitlisted member changes to a confirmed booking, their waitlist entry changes to promoted, and one in-app promotion notice appears.
6. Create a class less than 12 hours away, book it, and confirm cancellation is disabled/rejected by the seeded policy.

## Day 42 dashboard

1. Open `/app/dashboard` as `member@ypgym.dev` and confirm membership/expiry, QR eligibility, crowdedness, upcoming bookings, unread notifications, active announcements, and quick actions use live data.
2. Cancel or create a booking and return to the dashboard; the upcoming card must update.
3. Use an expired, frozen, cancelled, revoked, or no-membership test account and confirm the restricted QR and membership message without a crash.
4. Verify `/app/dashboard`, `/app/classes`, `/app/bookings`, and `/admin/pt-assignments` at desktop, tablet, and mobile widths when the interactive browser is available.

The exact policy and endpoint details are in `docs/api/classes-booking-dashboard.md` and `docs/policies/business-rules.md`.
