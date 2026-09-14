# Examiner demo script

Run from a disposable development stack using the commands in `README.md` and `mobile/README.md`. All seeded accounts use `YPGymDemo123!`; do not use real personal or payment data.

1. **Member web:** Sign in as `member@ypgym.dev`, inspect membership and expiry, open QR, browse classes, book/cancel a class, review bookings, notifications, attendance, invoices, and profile/preferences.
2. **Member native:** Start Expo against the same API, sign in manually, show the dashboard, QR expiry guard, class search/booking, and profile. Record screenshots only after the authenticated flow is confirmed.
3. **Staff:** Sign in as `staff@ypgym.dev`, open attendance operations, filter sessions, and demonstrate reason-required manual close. Attempt manager analytics and record the expected 403/denied state.
4. **Manager:** Sign in as `manager@ypgym.dev`, review peak-hours heatmap and the persisted analytics summary. Repeat the request inside 60 seconds to show the bounded cache metadata.
5. **Admin:** Review CRM, billing/invoices and exact-filter export, audit log, class schedule, broadcasts, configuration, and trainer assignment. Demonstrate one sensitive action with its audit entry.
6. **PT:** Sign in as `pt@ypgym.dev` and show the protected trainer dashboard.
7. **Recovery:** Stop or pause the API briefly to demonstrate loading/error/retry UI, then restore services. Do not leave a failed service running for a release screenshot.

Evidence indexes belong under `docs/design/evidence/`; the route map and release tracker must be updated with the actual date, viewport/device, and observed result.
