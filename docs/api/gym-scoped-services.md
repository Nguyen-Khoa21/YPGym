# Gym-scoped memberships, payments, classes and broadcasts

All paths are under `/api/v1`. PostgreSQL is authoritative. Every rule below is enforced by the backend; hiding a control in React is only presentation.

## Membership checkout and renewal

| Endpoint | Gym behavior |
|---|---|
| `POST /payments/payos/create` | Accepts `gym_id`. A first membership requires it (`422 GYM_SELECTION_REQUIRED`). A renewal defaults to the member's previous home gym and may name another active gym. An unknown or inactive gym returns `404`. |
| `GET /memberships/attendance-benefit/me?plan_id=&gym_id=` | Same gym resolution. The attendance benefit is measured at the member's current home gym when one exists, using that gym's timezone. |
| `POST /memberships/purchase`, `POST /admin/members/{id}/membership` | Same resolution for the mock and manual paths. Admin must choose the gym (`422 GYM_SCOPE_REQUIRED` otherwise). A manager's gym comes from the workforce assignment, and naming a different gym is rejected. |

The chosen gym is stored on `payments.gym_id` when the payment is created. The member's `home_gym_id` changes only when payment success is applied, never when checkout starts. Replaying an idempotency key with a different plan or gym returns `409 IDEMPOTENCY_KEY_REUSED`.

If the gym is deactivated before the payOS webhook arrives, the payment moves to `paid_review`, the membership is not changed, and an audit record is written for manual resolution (see `payos-payments.md`).

The membership confirmation, invoice product name, in-app notification and audit metadata name the gym. Billing, invoice and payment responses carry `gym_id` and `gym_name`. `GET /admin/payments` is admin-only.

## Classes

`classes.gym_id` is required. The existing `location` text stays as the room or studio label and is no longer the gym identity.

- `GET /classes/upcoming?gym_id=` lists one gym's classes. Without `gym_id` it uses the member's home gym. Each class and the list response include `gym_id`.
- Room overlap is checked within the gym. Trainer overlap stays global because one person cannot teach two classes at once.
- Class administration (list, create, update, cancel, trainers) is admin-only. `GET /classes` takes `gym_id` and falls back to District 1 when it is omitted. Create and update reject an unknown or inactive gym.
- A paid class checkout is refused with `409 CLASS_GYM_INACTIVE` if the class's gym is inactive. Class payments, invoices and notifications carry the class's gym.

## Broadcasts

`broadcast_announcements.gym_id` is nullable. `NULL` means chain-wide.

| Actor | Create | List and edit |
|---|---|---|
| Admin | One active gym, or all locations when `gym_id` is omitted | All broadcasts |
| Manager | Always the manager's assigned gym; naming a different gym is rejected | Own gym only. Chain-wide broadcasts cannot be edited. |
| Member | not allowed | Chain-wide broadcasts plus the home gym's broadcasts |

## Migration `20261109_0021`

Adds `payments.gym_id`, backfilled from the linked membership's home gym, then the linked class's gym, then District 1. It then becomes `NOT NULL` with a foreign key and an index on `(gym_id, created_at)`. Existing payment history is preserved.

## Not in this package

The Message textarea repair belongs to the form-reliability package. Dashboard layout, staff shift gating and the owner/manager workspaces are covered by later packages. Mobile clients keep working through additive fields and by sending no gym, which resolves to the member's previous gym.
