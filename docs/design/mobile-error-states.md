# Mobile Error-State Guidance

The Expo app starts later in the schedule, but mobile screens must use the same business-state language as the web app.

## Required States

- Loading: skeleton or spinner with a short label.
- Empty: explain that there is no membership, class, booking, invoice or attendance record yet.
- API error: display backend `error.message` and a retry action when safe.
- Permission denied: explain that the account role or membership status blocks the action.
- Offline/network: tell the user the app cannot reach the backend.

## Screens Covered Later

- Mobile Member Dashboard
- Mobile Membership Renewal Selection
- Mobile Renewal Success
- Mobile QR Check-in
- Mobile Class Booking
- Mobile Member Profile

