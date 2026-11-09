# Staff in-person registration, QR checkout and cash (Package 16)

Staff, managers and the owner register a walk-in member and take payment at the desk. The gym and the price are always decided by the server.

| Endpoint | Roles | Notes |
|---|---|---|
| `POST /staff/members` | staff (on shift), manager, admin | Body `name`, `email`, `phone`, optional `gym_id` (owner must send it; staff or managers naming another gym get `403`). Creates a verified member with `must_change_password=true`, `registration_channel='in_person'`, `registered_by_user_id`. Returns the temporary password once with `Cache-Control: no-store`. Duplicate email or phone return the online codes `EMAIL_ALREADY_EXISTS` and `PHONE_ALREADY_EXISTS` (`409`). 30 per hour per actor. |
| `POST /staff/members/{user_id}/membership-checkout` | same | Body `plan_id`, `idempotency_key`, optional `gym_id` (owner). Creates a pending payOS payment at the actor's gym and returns `checkout_url`, `amount_vnd`, `expires_at` and `qr_code` (payOS payload; may be absent on a replay, then encode `checkout_url`). The member's home gym changes only after the verified payOS webhook. A repeated key returns the same payment. |
| `POST /staff/members/{user_id}/membership-cash` | same | Same body. Records a succeeded payment with `provider='cash'` and a `CASH-` reference, an invoice, receipt emails and an audit row `membership.cash_payment.recorded` ("Cash payment received at {gym}"). The amount always comes from the plan price. A repeated key creates nothing new. Unknown body fields (for example `amount`) are `422`. |
| `GET /staff/payments/{payment_id}` | same | Returns `id`, `status`, `member_name`, `plan_name`, `gym_name` for staff-created QR payments at the actor's gym only; anything else is `404`. |

Who may be served: the owner may serve any member. Staff and managers may serve members registered in person; a member whose latest membership is at another gym is `403`. Looking up existing online members is out of scope.

Error codes added: `SHIFT_REQUIRED` (existing, now also on these endpoints), `CASH_REQUIRES_STAFF`, `IDEMPOTENCY_KEY_REUSED` (existing).

Privacy: the temporary password is never stored in clear text, logged or written to audit rows; `member.registered_in_person` records only the actor, the gym and the channel.
