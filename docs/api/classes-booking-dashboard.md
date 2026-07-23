# Trainers, class booking, waitlist, and dashboard API

All paths are under `/api/v1`. Errors use the shared `{ "error": { "code", "message", "details" } }` envelope.

## Trainer profiles

| Method and path | Roles | Purpose |
|---|---|---|
| `GET /trainers` | Public | Active member-safe trainer cards with at most three upcoming assigned classes. |
| `GET /trainers/{trainer_id}` | Public | One active member-safe trainer card. |
| `GET /admin/trainers?active=true|false` | Manager, admin | Active/inactive profile management list. |
| `POST /admin/trainers` | Manager, admin | Create a profile with name, bio, specialty, availability, and optional existing PT user link. |
| `PATCH /admin/trainers/{trainer_id}` | Manager, admin | Update member-safe profile fields or the optional PT user link. |
| `POST /admin/trainers/{trainer_id}/deactivate` | Manager, admin | Deactivate a profile after future scheduled classes are reassigned. |

Create/update/deactivate write audit records. Deactivation returns `409 CONFLICT` with future class IDs when reassignment is still required. Invalid or already-linked PT user IDs return `422 TRAINER_USER_INVALID` or `409 CONFLICT`.

## Member classes and bookings

| Method and path | Roles | Purpose |
|---|---|---|
| `GET /classes/upcoming` | Member | Future classes with capacity, confirmed count, remaining places, trainer card, member booking/waitlist state, and membership eligibility. |
| `GET /classes/{class_id}` | Member | One class and the authenticated member's current state. |
| `POST /classes/{class_id}/book` | Member | Create or reactivate one confirmed booking while holding the class row lock. |
| `GET /bookings/me` | Member | Bounded booking/waitlist history plus configured cancellation window and per-booking cutoff. |
| `POST /bookings/{booking_id}/cancel` | Owning member | Cancel an eligible confirmed booking and promote the waitlist in the same transaction. |

Important booking errors:

- `403 MEMBERSHIP_REQUIRED` or `MEMBERSHIP_INELIGIBLE`
- `409 CLASS_UNAVAILABLE` or `CLASS_ALREADY_STARTED`
- `409 BOOKING_EXISTS` or `WAITLIST_EXISTS`
- `409 CLASS_FULL`
- `409 LATE_CANCELLATION`, including the calculated cutoff
- `404 RESOURCE_NOT_FOUND` for a missing or non-owned booking

## Waitlist

| Method and path | Roles | Purpose |
|---|---|---|
| `POST /classes/{class_id}/waitlist` | Member | Join only when confirmed capacity is full and the configured waitlist has room. |
| `DELETE /classes/{class_id}/waitlist` | Owning member | Leave a waiting entry; a promoted entry must be managed through its booking. |

Queue order is deterministic by stored monotonic `position`, then `created_at`, then UUID. Cancellation automatically promotes the earliest eligible entry. Ineligible entries transition to `cancelled` and the scan continues. The promoted entry and confirmed booking are updated atomically. Preference-aware in-app and development-email notification records use a unique dedupe key per class, waitlist entry, position, and channel.

## Member dashboard

| Method and path | Roles | Purpose |
|---|---|---|
| `GET /dashboard/me` | Member | Mobile-reusable bounded composite of identity, latest membership/effective status, QR eligibility/reason, crowdedness, three upcoming bookings, three active waitlists, unread count, three most recent unread in-app notifications, active broadcasts, and typed quick actions. |

The endpoint only uses the authenticated user ID. It composes existing lifecycle, booking, notification, broadcast, and crowdedness services rather than copying their business rules.

## Capacity and cancellation transaction

Booking, waitlist join/leave, cancellation, and promotion lock the affected `classes` row with PostgreSQL `FOR UPDATE`. The lock serializes confirmed-count checks and waitlist position allocation for one class. The configured `class_cancellation_window_hours` cutoff is inclusive: a cancellation at the exact cutoff is accepted; the first instant after it is late.
