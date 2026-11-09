# Gym-aware API reference

All paths are under `/api/v1`. This page lists every endpoint whose result depends on a gym, with the role, the scope rule and the error codes. It links to the detailed pages instead of copying them: [gym-scoped services](gym-scoped-services.md), [traffic analytics](traffic-analytics.md), [payOS payments](payos-payments.md), [staff operations](staff-operations.md). The router files in `backend/app/api/v1/endpoints` are the source of truth, and the endpoint list was taken from the application's OpenAPI document.

## How the gym is chosen

`GymScopeService` (`backend/app/services/gym_service.py`) applies one rule everywhere.

| Caller | Rule |
|---|---|
| Owner (`admin`) | Uses `gym_id` when given. When missing, a few list endpoints cover all gyms; the rest return `422 GYM_SCOPE_REQUIRED`. |
| Manager, staff, PT | The gym of the single active `workforce_gym_assignments` row. A different `gym_id` returns `403`. No assignment returns `403 GYM_ASSIGNMENT_REQUIRED`. |
| Member | The gym of the latest membership (`home_gym_id`). A different `gym_id` returns `403`. No membership returns `403 GYM_MEMBERSHIP_REQUIRED`. |
| Any | An unknown or inactive gym returns `404`. |

## Error codes

| Code | Status | Meaning |
|---|---|---|
| `PERMISSION_DENIED` | 403 | The caller named a gym outside their scope. |
| `GYM_SCOPE_REQUIRED` | 422 | The owner must choose a gym for this operation. |
| `GYM_SELECTION_REQUIRED` | 422 | A first membership checkout needs `gym_id`; the owner creating a workforce account must also pick a gym. |
| `GYM_ASSIGNMENT_REQUIRED` | 403 | Workforce account has no active gym assignment. |
| `GYM_MEMBERSHIP_REQUIRED` | 403 | Member has no gym-linked membership. |
| `MEMBERSHIP_GYM_MISMATCH` | 403 | Scanner's gym is not the member's home gym. |
| `ATTENDANCE_GYM_MISMATCH` | 403 | Check-out at a gym other than the one holding the session. |
| `SHIFT_REQUIRED` | 403 | Staff must clock in at the assigned gym before attendance operations. |
| `CLASS_GYM_INACTIVE` | 409 | A paid class checkout was refused because the class's gym is inactive. |
| `IDEMPOTENCY_KEY_REUSED` | 409 | An idempotency key was replayed with a different plan or gym. |

## Gym locations

| Method and path | Role | Gym rule |
|---|---|---|
| `GET /gyms` | Public | Active gyms only. |
| `GET /gyms/me` | Any signed-in role | The caller's own gym (see rule above). Registered before `/{gym_id}`. |
| `GET /gyms/{gym_id}` | Public | Active gym; `404` otherwise. |
| `GET /gyms/{gym_id}/crowdedness` | Signed in | `require_access`: owner any gym, others own gym only. |
| `GET /admin/gym-locations` | Owner | All gyms including inactive. |
| `POST /admin/gym-locations` | Owner | Creates a gym. Duplicate slug is a conflict. |
| `PATCH /admin/gym-locations/{gym_id}` | Owner | Edits a gym. |
| `GET /admin/gym-locations/workforce/assignments` | Owner | Optional `gym_id` filter. |
| `PUT /admin/gym-locations/workforce/assignments` | Owner | Moves a manager, staff or PT to a gym. One active assignment per user is a unique index. |

## Attendance and occupancy

| Method and path | Role | Gym rule |
|---|---|---|
| `POST /attendance/check-in`, `POST /attendance/check-out` | Scanner device credential | The device's `iot_devices.gym_id` decides the gym. A member whose home gym differs is refused with `403 MEMBERSHIP_GYM_MISMATCH` at check-in. Check-out of a session that belongs to another gym is refused with `403 ATTENDANCE_GYM_MISMATCH`. Events and sessions carry the device's gym. |
| `POST /attendance/device/verify` | Scanner device credential | Returns the device's gym. |
| `GET /attendance/crowdedness` | Any signed-in role | Owner: `gym_id` required (`422 GYM_SCOPE_REQUIRED`). Others: own gym. |
| `GET /attendance/traffic-summary` | Member | Home gym. |
| `GET /attendance/me` | Member | Own sessions. |
| `GET /attendance/admin` | Staff (open shift), manager, owner | Owner without `gym_id` lists every gym. Staff without an open shift at the assigned gym: `403 SHIFT_REQUIRED`. |
| `POST /attendance/admin/{session_id}/manual-close` | Staff (open shift), manager, owner | The session's gym must be inside the caller's scope. Same `SHIFT_REQUIRED` rule. |
| `WS /attendance/realtime` | Member and operations roles | First frame `{type: "authenticate", access_token, gym_id?}`. The server resolves the gym with the same rule and only sends events for that gym. Close codes: 4400 malformed, 4401 auth failed, 4403 role or password-change blocked, 4408 auth timeout. |

## Analytics

| Method and path | Role | Gym rule |
|---|---|---|
| `GET /admin/analytics/summary` | Manager, owner | Owner without `gym_id` covers all gyms. Revenue is included only for the owner. |
| `GET /admin/analytics/peak-hours` | Manager, owner | Owner must pass `gym_id`. |
| `GET /admin/analytics/traffic-summary` | Manager, owner | Owner defaults to District 1 when `gym_id` is omitted. |

## Staff shifts

| Method and path | Role | Gym rule |
|---|---|---|
| `GET /staff/shifts/me`, `POST /staff/shifts/clock-in`, `POST /staff/shifts/clock-out` | Staff, PT | A shift is stored with the assigned gym. |
| `GET /admin/staff-shifts` | Manager, owner | Manager: own gym. Owner: any gym or all. |
| `GET /admin/staff-accounts`, `POST /admin/staff-accounts` | Manager, owner | A manager's new account goes to the manager's gym. The owner must choose a gym (`422 GYM_SELECTION_REQUIRED`). |

## Memberships, payments, classes and broadcasts

| Method and path | Role | Gym rule |
|---|---|---|
| `POST /payments/payos/create` | Member | `gym_id` rules in [gym-scoped services](gym-scoped-services.md); stored on `payments.gym_id`. |
| `POST /payments/payos/webhook`, `GET /payments/payos/{order_code}` | payOS, member | Home gym changes only when payment success is applied. |
| `GET /memberships/attendance-benefit/me` | Member | Same gym resolution as checkout. |
| `POST /memberships/purchase`, `POST /admin/members/{user_id}/membership` | Member, manager, owner | Owner must choose a gym; a manager's gym is fixed. |
| `GET /billing/admin/payments` | Owner | Payments carry `gym_id` and `gym_name`. |
| `GET /classes/upcoming` | Member | `gym_id`, default home gym. |
| `GET/POST /admin/classes`, `PATCH /admin/classes/{class_id}`, `POST /admin/classes/{class_id}/cancel` | Owner | `classes.gym_id` required; inactive gym rejected. |
| `GET/POST /admin/broadcasts`, `PATCH /admin/broadcasts/{broadcast_id}` | Manager, owner | Manager: own gym only; the owner may publish chain-wide. |
| `GET /notifications/broadcasts/active` | Member | Chain-wide plus home gym. |

## Realtime and cache keys per gym

- Channel: `ypgym:attendance:{gym_id}:events:v1`; listener pattern `ypgym:attendance:*:events:v1`.
- Occupancy cache: `ypgym:attendance:occupancy:{gym_id}`.
- Analytics cache: `ypgym:analytics:summary:` followed by the gym and the revenue flag.

## Compatibility

Mobile apps do not send `gym_id`. They keep working through the member's previous gym; the scanner and member apps were not updated for gyms in this release.
