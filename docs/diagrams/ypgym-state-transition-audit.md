# YPGym state-transition audit and mismatch report

## Audit baseline

- Inspected commit: `4b7523670b04bc8adce38a11baa2feb486cc4f4d` (`main`, matching `origin/main`).
- Previous supplied baseline: `cc6a01724bdfac55255c4c89c502b51b245d1e6b`.
- The repository already contained unrelated modified/untracked files before this diagram work. They were preserved.
- Production behavior was not changed by this package.

## Persisted and temporary states found

- Membership: `pending_verification`, `active`, `expiring_soon`, `expired`, `frozen`, `cancelled`, `revoked`.
- Approval request: `pending`, `approved`, `rejected`.
- Payment: `pending`, `paid`, `succeeded`, `failed`, `cancelled`, `expired`, `paid_review`.
- Class: `scheduled`, `cancelled`, `completed`.
- Class booking: `pending_payment`, `confirmed`, `cancelled`, `expired`, `payment_failed`, `refunded`.
- Waitlist: `waiting`, `promoted`, `cancelled`.
- Refund marker: `none`, `required`, `resolved`.
- Attendance session: `active`, `checked_out`, `timed_out`, `manual_closed`.
- Registration: persisted user boolean `is_email_verified`; verification token timestamps `expires_at` and `used_at`.
- QR: JWT claims plus temporary Redis active-JTI and JTI-owner mappings. QR outcomes are not PostgreSQL business states.

## Verified implementation improvements at the current commit

- Promoted waitlist members can start checkout because an existing `pending_payment` hold is accepted idempotently and a pending payment is attached.
- Refund resolution can move `expired` and `payment_failed` bookings to `refunded`, matching late paid class review paths.
- The integration suite adds coverage for promoted checkout and late paid/refund resolution.
- Membership synchronization now permits `active`, `expiring_soon`, `frozen`, and `expired` to transition to `pending_verification` when the account is unverified. The scheduled lifecycle path persists the correction and integration coverage verifies it. Access checks deny the derived ineligible state immediately; the scheduled sync remains the durable reconciliation path.
- Class completion now has two runtime writers. A minute-scheduled Celery task locks and completes scheduled classes whose `end_at` has passed. The assigned personal trainer can confirm a scheduled class after `start_at` through the PT workspace. Both paths use `transition_class`, write one audit record, and the PT endpoint is idempotent for an already-completed class.
- Class-payment hold release now promotes the earliest eligible waiting member in the same class-locked transaction. Verified failure/cancellation callbacks, owner polling, the scheduled expiry sweep, checkout cleanup, and late-success review all reuse `WaitlistPromotionService`; unrelated checkout cannot bypass a promoted queue member.

## Remaining mismatches and limitations

| ID | Finding | Evidence and impact | Diagram treatment |
| --- | --- | --- | --- |
| M2 | `expired -> active` is declared but not used for renewal. | Membership lookup for purchase only selects `active`/`expiring_soon`; an expired purchase creates a new `active` row. | Membership diagram notes the rule-only edge is not a runtime mutation of the expired row. |
| M5 | Late membership success has no review/reconciliation path. | `late_class_success` is intentionally restricted to class products. A successful membership callback after `failed/cancelled/expired` receives `RspCode 02` and does not enter `paid_review`. | Payment diagram scopes late review arrows to class payments. |
| M6 | Internal refund resolution is not provider reversal confirmation. | `resolve_class_refund` updates booking/refund state and audit only; it does not invoke VNPay query/refund APIs. | Payment and booking diagrams label this explicitly. |
| M7 | QR tokens are rotating, not single-use, and have no explicit revoke endpoint. | A valid scan does not delete the JTI. Check-in has a temporary replay key; check-out does not. Superseding issuance or TTL expiry is the only revocation-like behavior. | QR diagram separates current, duplicate-scan, superseded, expired and inactive outcomes. |
| M8 | Email verification has no resend endpoint or verification-row lock. | Token lookup is a normal select; expiry strands local registrations unless an operator intervenes. Concurrent valid requests are not serialized, although both converge on the same verified/used values. | Registration diagram notes both limitations. |
| M9 | Some narrative API documentation is stale. | `docs/api/vnpay-payments.md` omits `paid_review` transitions; `docs/api/classes-booking-dashboard.md` still describes membership eligibility and a configured cancellation window even though paid class booking requires only verified email and member cancellation is allowed until class start. | This report is authoritative for the diagram package; those narrative files were not edited. |
| M10 | Web payment typing omits legacy `succeeded`. | `frontend/src/types/api.ts` models current VNPay states but the backend may return legacy/mock `succeeded` payment records. | Payment diagram retains `succeeded` as a distinct terminal compatibility state. |

## Guards, concurrency and side effects verified

- VNPay IPN verifies signature, merchant code, integer VND amount and provider success codes; payment, user, booking and class rows are locked before fulfillment.
- Payment and invoice uniqueness constraints make duplicate fulfillment fail atomically; terminal callbacks are explicitly idempotent through `RspCode 02`.
- Class checkout locks the class and booking, counts confirmed bookings plus unexpired payment holds, and uses a unique `(user_id, idempotency_key)` payment key.
- Class completion locks each class row. The automatic sweep selects ended scheduled rows with `FOR UPDATE SKIP LOCKED`; manual confirmation derives PT identity from the authenticated user, requires assignment, and rejects pre-start confirmation.
- Waitlist promotion locks ordered queue rows and executes inside the cancellation or payment-release transaction; it queues channel-specific deduplicated promotion notifications.
- Attendance uses row locks plus a PostgreSQL partial unique index for one active session per user; closure writes immutable events and reconciles occupancy.
- QR validation fails closed on Redis outages; token material/JTIs are not logged, and event metadata stores a hash of the JTI.
- Registration stores hashed verification tokens, commits user/token/notification atomically, rate-limits token use, and keeps delivery failure private.

## Resolution boundary

Finding M1 is resolved by commit `7f15109`. Findings M3 and M4 are resolved in the current working tree by the audited class-completion and payment-release implementations plus integration coverage. Findings M2 and M5–M10 remain documentation-visible limitations until separately approved for implementation.

## Diagram validation results

- All nine Mermaid sources rendered successfully with Pretty Mermaid using the `zinc-light` theme.
- All nine native Draw.io sources passed structural validation with zero errors. The remaining warnings are the intentional overlapping circles used for UML final-state markers plus three documented routing warnings in the dense class-booking/payment diagram; the other eight diagrams have no connector crossings or through-node routes.
- All nine PNG exports have valid PNG signatures and end markers, contain embedded `mxGraphModel` data, and render at 3,566 × 2,009 pixels except the wider terminal-membership diagram at 3,691 × 2,009 pixels.
- Visual review checked every PNG for title and label visibility, clipping, contrast, connector routing and 16:9 presentation legibility. Membership was split into verification reconciliation, coverage/freeze, and cancellation/revocation views; class lifecycle remains split from booking/payment.

