# YPGym verified state-transition tables

Audit target: commit `4b7523670b04bc8adce38a11baa2feb486cc4f4d` on `main` (also `origin/main`). These tables describe repository behavior at that commit. State names are exact stored values unless a row explicitly says the state is derived or logical.

## Membership lifecycle

| Current state | Event | Guard | Action/side effect | Next state | Source function | Failure/error |
| --- | --- | --- | --- | --- | --- | --- |
| no membership row | Mock/staff purchase or verified VNPay success | Active plan; self-service user verified; staff path may target an unverified user | Create membership, payment/invoice, email outbox/notification, audit when manual | `active` | `MembershipService.purchase`; `MembershipService.finalize_vnpay_payment` | Plan/payment/idempotency errors roll back |
| `active` or `expiring_soon` | Renewal | Current row selected with `FOR UPDATE`; coverage not expired or VNPay renewal was reserved | Extend expiry, set plan, keep/transition to `active`, issue invoice | `active` | `MembershipService.purchase`; `MembershipService.finalize_vnpay_payment` | Revoked latest membership blocks self-service |
| `expired` | Purchase after expiry | Expired rows are not selected by `get_current_for_user[_for_update]` | Create a new membership row; old row stays expired | new row `active` | `MembershipService.purchase`; `MembershipService.finalize_vnpay_payment` | The central `expired -> active` rule is not used by this path |
| `pending_verification` | Hourly lifecycle sync or access check | User now verified; date/freeze predicates decide target | Persist derived status | `active`, `expiring_soon`, `frozen`, or `expired` | `MembershipLifecycleService.synchronize_membership_statuses`; `require_eligible_membership` | Invalid target is rejected by centralized FSM |
| `active` | Hourly lifecycle sync | Verified; 0–7 days remain | Persist warning state | `expiring_soon` | `MembershipLifecycleService.synchronize_membership_statuses` | Transaction rolls back on invalid transition |
| `active` or `expiring_soon` | Approved freeze / hourly sync | Request pending; today is inside approved freeze range | Store range, request decision and audit; persist freeze when effective | `frozen` | `MembershipLifecycleService.decide_freeze_request`; `synchronize_membership_statuses` | Duplicate/open request and invalid-state conflicts |
| `frozen` | Hourly lifecycle sync | Freeze ended or expiry passed | Derive from expiry distance | `active`, `expiring_soon`, or `expired` | `MembershipLifecycleService.synchronize_membership_statuses` | Invalid transition aborts worker transaction |
| `active`, `expiring_soon`, or `frozen` | Cancellation approval | Pending cancellation request; reviewer decision supplied | Store request outcome, set `cancelled_at`, audit | `cancelled` | `MembershipLifecycleService.decide_cancellation_request` | Terminal status has no outgoing transition |
| any non-terminal membership | Admin revoke | Latest/current membership exists; reason supplied | Store reviewer/reason/timestamp and audit | `revoked` | `MembershipLifecycleService.revoke_membership` | Only admin endpoint authorization may invoke it |
| `active`, `expiring_soon`, `frozen`, or `expired` | User becomes unverified | `is_email_verified = false`; membership is non-terminal | Access checks deny immediately from the derived status; scheduled lifecycle sync persists the correction | `pending_verification` | `derive_membership_status`; `require_eligible_membership`; `synchronize_membership_statuses`; `transition_membership` | Transition is permitted and integration-tested; terminal `cancelled`/`revoked` remain unchanged |
| request `pending` | Reviewer approves/rejects | Request row locked | Store reviewer, decision reason, review timestamp; approved cancellation/freeze may change membership | request `approved` or `rejected` | `decide_freeze_request`; `decide_cancellation_request` | Repeated decision is rejected by request FSM |

## VNPay payment lifecycle

| Current state | Event | Guard | Action/side effect | Next state | Source function | Failure/error |
| --- | --- | --- | --- | --- | --- | --- |
| no payment row | Create membership/class checkout | Feature configured; validated product/price; unique idempotency key and transaction reference | Store expiry and provider metadata; class checkout also reserves capacity | `pending` | `VNPayPaymentService.create_payment`; `create_class_payment` | Rate, eligibility, capacity, price, unique-key errors |
| no payment row | Mock purchase or staff enrollment | Local confirmation flag or authorized staff path | Create invoice and membership synchronously | `succeeded` | `MembershipService.purchase` | `succeeded` is terminal legacy/mock compatibility |
| `pending` | Verified successful IPN | Signature, merchant, amount, response and transaction status valid; row locked | Set provider fields and `paid_at`; fulfill membership or class; invoice, notifications, emails, audit | `paid` | `VNPayPaymentService.process_ipn`; `_finalize_class_payment`; `MembershipService.finalize_vnpay_payment` | Integrity error returns VNPay `RspCode 99` and rolls back |
| `pending` | Verified non-success IPN | Valid signature/merchant/amount; response code not `00` | Audit outcome; class booking becomes `payment_failed` | `failed` | `VNPayPaymentService.process_ipn` | Commit failure returns `RspCode 99` |
| `pending` | Verified customer cancellation | `vnp_ResponseCode = 24` | Audit outcome; class booking becomes `payment_failed` | `cancelled` | `VNPayPaymentService.process_ipn` | Commit failure returns `RspCode 99` |
| `pending` | Expiry read or scheduled expiry | `expires_at <= now` | Audit expiry; linked live class hold becomes `expired` | `expired` | `get_status`; `expire_pending`; `_expire_payment_if_due`; Celery `expire_vnpay_payments` | None; locked rows use `SKIP LOCKED` in batch |
| `pending` | Verified class success but hold cannot be fulfilled | Hold is stale/not current, class unavailable/started, or confirmed capacity full | Do not confirm seat; mark booking refund required; audit | `paid_review` | `_finalize_class_payment` | Manual resolution required |
| `failed`, `cancelled`, or `expired` | Verified late class success | Product is class booking and callback reports success | Mark booking refund required; audit | `paid_review` | `process_ipn`; `_finalize_class_payment` | Membership late success is not accepted into review |
| any non-`pending` state except eligible late class success | Duplicate callback | Terminal payment already stored | No mutation | unchanged | `VNPayPaymentService.process_ipn` | VNPay `RspCode 02` / `Order already confirmed` |
| any | Invalid signature/merchant | Signature fails, duplicate query key, or terminal code mismatch | No mutation | unchanged | endpoint `vnpay_ipn`; `process_ipn` | VNPay `RspCode 97` |
| any | Amount mismatch | Protocol amount differs from stored integer VND amount | No mutation | unchanged | `process_ipn` | VNPay `RspCode 04` |
| `paid_review` | Admin records class refund resolution | Linked booking has `refund_status = required`; reason supplied | Booking becomes `refunded`, refund flag becomes `resolved`, audit | payment stays `paid_review` | `resolve_class_refund` | No provider refund/reversal call is made |

## Class, booking, waitlist and refund lifecycle

| Current state | Event | Guard | Action/side effect | Next state | Source function | Failure/error |
| --- | --- | --- | --- | --- | --- | --- |
| no class row | Admin creates class | Future, timezone-aware valid range; no trainer/location overlap | Store schedule and audit | class `scheduled` | `ClassService.create` | Validation or overlap conflict |
| class `scheduled` | Admin cancels class | Class row locked | Cancel live payments/bookings and waiting entries; require refunds for paid confirmed seats; audit | class `cancelled` | `ClassService.cancel` | Only scheduled classes can be cancelled |
| class `scheduled` | Completion | Central rule permits it | No runtime writer found | class `completed` | `CLASS_TRANSITIONS` only | Unreachable through current service/endpoints/tasks |
| no booking row, or reusable terminal row | Checkout | Verified email, future scheduled class, price set, capacity available, no unresolved refund | Reserve seat until min(payment TTL, class start); create pending payment | `pending_payment` | `VNPayPaymentService.create_class_payment` | Full class, active payment, refund review, idempotency conflicts |
| `pending_payment` | Verified successful IPN | Payment is current; hold live; class scheduled/future; confirmed count below capacity | Confirm booking, clear hold, invoice/email/notification/audit | `confirmed` | `_finalize_class_payment` | Otherwise payment goes `paid_review` and booking expires if still pending |
| `pending_payment` | Verified failure/cancellation | Current linked payment | Clear reservation; promote earliest eligible waitlist entry and notify | `payment_failed` | `process_ipn`; `_release_current_class_hold`; `WaitlistPromotionService.promote` | Repeated callback is idempotent; no eligible entry leaves capacity open |
| `pending_payment` | Payment/hold expiry | Due by clock | Clear reservation; audit payment expiry; promote earliest eligible waitlist entry and notify | `expired` | `_expire_payment_if_due`; `create_class_payment` cleanup; `WaitlistPromotionService.promote` | Unrelated checkout receives `CLASS_FULL` after a queue promotion |
| `pending_payment` | Member/class cancellation | Before class start for member path | Cancel current payment, clear/release hold, audit; member cancellation calls promotion | `cancelled` | `BookingService.cancel`; `ClassService.cancel` | Member cancellation after start is rejected |
| `confirmed` | Member/class cancellation | Before start for member; class must be scheduled for admin path | Set cancellation metadata; paid booking sets refund `required`; member cancellation promotes queue | `cancelled` | `BookingService.cancel`; `ClassService.cancel` | Already terminal member cancellation is idempotent |
| `cancelled`, `expired`, `payment_failed`, or `refunded` | New checkout or waitlist promotion | Capacity available; no unresolved refund | Reuse row, reset hold/payment metadata and refund marker as applicable | `pending_payment` | `create_class_payment`; `WaitlistPromotionService.promote` | Invalid centralized transition or capacity conflict |
| refund `none` | Paid booking cancellation or late class success | Settled/verified money requires manual handling | Flag staff review | refund `required` | `BookingService.cancel`; `ClassService.cancel`; `_finalize_class_payment` | Checkout is blocked while required |
| refund `required` | Admin records resolution | Reason supplied; payment and booking rows locked | Audit; booking becomes `refunded` | refund `resolved` | `VNPayPaymentService.resolve_class_refund` | No provider reversal is confirmed |
| refund `resolved` | New checkout/promotion | Booking row is reusable and capacity available | Clear old resolution marker | refund `none` | `create_class_payment`; `WaitlistPromotionService.promote` | Central FSM rejects other targets |
| no waitlist row or prior terminal entry | Join/rejoin | Verified; class future/scheduled and full; queue below configured limit | Allocate monotonically increasing position | `waiting` | `BookingService.join_waitlist` | Not full, duplicate queue, queue full, or active booking |
| `waiting` | Seat opens through member cancellation or payment hold release | Candidate verified, class scheduled/future, no active booking, no unresolved refund | Create/reuse `pending_payment` hold; queue deduplicated per-channel promotion notifications | `promoted` | `BookingService.cancel`; `VNPayPaymentService`; `WaitlistPromotionService.promote` | Ineligible candidates are cancelled and skipped |
| `waiting` | Leave, class cancellation, or ineligible promotion candidate | Row/class locked | Release queue entry | `cancelled` | `leave_waitlist`; `ClassService.cancel`; `_promote` | Promoted entry cannot be left through waitlist endpoint |
| `promoted` or `cancelled` | Rejoin | Class again full and member eligible | Allocate new position | `waiting` | `join_waitlist` | Active booking prevents rejoin |

## Attendance session lifecycle

| Current state | Event | Guard | Action/side effect | Next state | Source function | Failure/error |
| --- | --- | --- | --- | --- | --- | --- |
| no session | Scanner check-in | Authenticated/rate-limited device; current QR; eligible membership; duplicate key accepted; no active session | Create session and immutable `check_in` event in one transaction; reconcile occupancy | `active` | `AttendanceService.check_in`; `AttendanceRepository.create_session` | Invalid device/token/membership; duplicate scan; active-session unique conflict |
| `active` | Scanner check-out | Authenticated device; current QR; active row locked | Set `closed_at`, create `check_out` event, reconcile occupancy | `checked_out` | `AttendanceService.check_out` | `NO_ACTIVE_SESSION` if none |
| `active` | Scheduled timeout | Checked in before configured cutoff; batch row locked with `SKIP LOCKED` | Set `closed_at`, create timeout event, reconcile occupancy | `timed_out` | `AttendanceService.close_timed_out_sessions`; Celery `close_timed_out_attendance` | Repeated worker skips non-active rows |
| `active` | Staff manual close | Staff/manager/admin; row locked; reason supplied | Set actor/reason/closed time, create event and audit, reconcile occupancy | `manual_closed` | `AttendanceService.manual_close` | Missing session is 404 |
| terminal attendance state | Repeated manual close | Session exists | Return existing state without mutation | unchanged | `AttendanceService.manual_close` | No new event/audit |

## QR token lifecycle (temporary Redis/JWT state)

| Current state | Event | Guard | Action/side effect | Next state | Source function | Failure/error |
| --- | --- | --- | --- | --- | --- | --- |
| no current token | Generate | Eligible membership; Redis available | Sign JWT; store active user→JTI and JTI→user keys with TTL | issued/current | `QrTokenService.generate` | `QR_STATE_UNAVAILABLE` if Redis write fails |
| issued/current | Generate newer token | Same eligibility guard | Delete previous JTI key; replace active pointer | old token superseded; new token current | `QrTokenService.generate` | This is the only revocation-like behavior |
| issued/current | Validate/use | JWT signature/type/sub/JTI valid; Redis mappings both match | Permit scanner flow; token remains active | valid use, then current | `QrTokenService.validate`; attendance check-in/out | Token is not consumed |
| issued/current | Repeat check-in inside duplicate window | Redis `SET NX` for scan JTI fails | Reject scan | `duplicate_scan` outcome | `AttendanceService.check_in` | HTTP 409 `DUPLICATE_SCAN` |
| duplicate-scan outcome | Window expires | Token/JTI TTL still live | Later validation may pass; active-session guard still applies | current | Redis TTL; `check_in` | Existing active session returns 409 |
| issued/current | JWT expiry | JWT `exp` elapsed | Reject | expired outcome | `QrTokenService.validate` | HTTP 400 `EXPIRED_TOKEN` |
| issued/current | Redis TTL/mapping absent | JTI or active pointer missing/mismatched | Reject | inactive/invalid outcome | `QrTokenService.validate` | HTTP 400 `INVALID_TOKEN` |
| issued/current | Newer token exists | Active pointer differs from presented JTI | Reject | superseded outcome | `QrTokenService.validate` | HTTP 409 `SUPERSEDED_TOKEN` |
| any | Redis read failure | State cannot be verified | Reject fail-closed | unavailable outcome | `QrTokenService.validate` | HTTP 503 `QR_STATE_UNAVAILABLE` |

## Registration and email verification lifecycle

| Current state | Event | Guard | Action/side effect | Next state | Source function | Failure/error |
| --- | --- | --- | --- | --- | --- | --- |
| no user row | Local registration | Rate limits; unique email and phone; valid request | Store password hash, member role/tier, welcome notification; create hashed verification token | `users.is_email_verified = false`; token unused | `AuthService.register`; `_create_email_verification` | Uniqueness conflict rolls back transaction |
| token unused | Verification request | Hash lookup finds token and user; `used_at IS NULL`; `expires_at >= now` | Set user boolean/timestamp and token `used_at` in one commit | user verified; token used | `AuthService.verify_email` | Invalid/missing token returns 400 |
| token unused | Time passes | `expires_at < now` | No mutation | token expired (derived) | `AuthService.verify_email` | `VERIFICATION_TOKEN_EXPIRED` |
| token used | Repeated verification | Token record still found | Return already verified response | unchanged | `AuthService.verify_email` | No new token/event |
| user unverified | Login | Credentials otherwise valid | No mutation | unchanged | `AuthService.login` | HTTP 403 `EMAIL_NOT_VERIFIED` |
| user verified | Login | Password valid | Issue signed access token | authenticated session (temporary) | `AuthService.login` | Invalid credentials return 401 |
| no user row | Verified OAuth registration | Provider email present and provider asserts verified | Create user with boolean true and timestamp; attach identity | `users.is_email_verified = true` | `OAuthService._resolve_profile` path | Provider-unverified email is rejected before creation |
| no user row | Staff provisioning | Authorized staff workflow | Create account directly verified | `users.is_email_verified = true` | `StaffService.create_member` | Authorization/uniqueness errors |
| registration committed | Verification email delivery fails | Mail transport unavailable | Log private warning; keep account and token | user remains unverified | `AuthService.register`; `_prepare_development_email` | No resend-verification endpoint exists |

