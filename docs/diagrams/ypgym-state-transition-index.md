# YPGym state-transition diagram index

All artifacts were verified against commit `4b7523670b04bc8adce38a11baa2feb486cc4f4d`. Editable sources are `.drawio`; embedded presentation exports are `.drawio.png`; Mermaid sources are synchronized structural references.

| Domain | Editable / export / Mermaid | Controlling code and functions |
| --- | --- | --- |
| Membership verification reconciliation | `ypgym-membership-state-transition.drawio`; `ypgym-membership-state-transition.drawio.png`; `ypgym-membership-state.mmd` | `backend/app/services/lifecycle_service.py` (`derive_membership_status`, `require_eligible_membership`, `synchronize_membership_statuses`); `backend/app/services/state_transitions.py` (`MEMBERSHIP_TRANSITIONS`); Celery `synchronize_memberships` |
| Membership coverage and freeze | `ypgym-membership-coverage-state-transition.drawio`; `ypgym-membership-coverage-state-transition.drawio.png`; `ypgym-membership-coverage-state.mmd` | `MembershipStatus`; `MEMBERSHIP_TRANSITIONS`; `derive_membership_status`; `decide_freeze_request`; `synchronize_membership_statuses`; `MembershipService.purchase/finalize_vnpay_payment` |
| Membership cancellation and revocation | `ypgym-membership-terminal-state-transition.drawio`; `ypgym-membership-terminal-state-transition.drawio.png`; `ypgym-membership-terminal-state.mmd` | `MembershipStatus`, `RequestStatus`; `MEMBERSHIP_TRANSITIONS`, `REQUEST_TRANSITIONS`; `decide_cancellation_request`; `revoke_membership`; `AuditRepository` |
| VNPay payment | `ypgym-vnpay-payment-state-transition.drawio`; `.drawio.png`; `ypgym-vnpay-payment-state.mmd` | `backend/app/models/billing.py` (`Payment` constraints); `backend/app/services/state_transitions.py` (`PAYMENT_TRANSITIONS`); `backend/app/services/payment_service.py` (`create_payment`, `create_class_payment`, `process_ipn`, `_finalize_class_payment`, `_expire_payment_if_due`, `resolve_class_refund`); `backend/app/repositories/billing_repository.py`; payment endpoints; Celery `expire_vnpay_payments` |
| Class booking and payment hold | `ypgym-class-booking-payment-state-transition.drawio`; `.drawio.png`; `ypgym-class-booking-payment-state.mmd` | `backend/app/models/classes.py` (`ClassBooking`); `BOOKING_TRANSITIONS`; `VNPayPaymentService.create_class_payment`, `_finalize_class_payment`, `_expire_payment_if_due`; `BookingService.cancel`; `ClassRepository` locking/capacity queries |
| Class, waitlist and refund | `ypgym-class-waitlist-refund-state-transition.drawio`; `.drawio.png`; `ypgym-class-waitlist-refund-state.mmd` | `ClassStatus`, `WaitlistStatus`, `RefundStatus`; `CLASS_TRANSITIONS`, `WAITLIST_TRANSITIONS`, `REFUND_TRANSITIONS`; `ClassService.create/cancel`; `BookingService.join_waitlist`, `leave_waitlist`; `WaitlistPromotionService.promote`; `VNPayPaymentService.resolve_class_refund` |
| Attendance session | `ypgym-attendance-session-state-transition.drawio`; `.drawio.png`; `ypgym-attendance-session-state.mmd` | `AttendanceSessionStatus`; `ATTENDANCE_TRANSITIONS`; `AttendanceService.check_in`, `check_out`, `manual_close`, `close_timed_out_sessions`; `AttendanceRepository`; attendance endpoints; Celery `close_timed_out_attendance` |
| QR token | `ypgym-qr-token-lifecycle.drawio`; `.drawio.png`; `ypgym-qr-token-lifecycle.mmd` | `QrTokenService.generate/validate`; `AttendanceService.check_in/check_out`; Redis key prefixes `ypgym:attendance:qr:*` and `ypgym:attendance:scan:*`; attendance endpoints |
| Registration and verification | `ypgym-registration-verification-state-transition.drawio`; `.drawio.png`; `ypgym-registration-verification-state.mmd` | `backend/app/models/user.py`; `backend/app/models/auth_token.py`; `AuthTokenRepository`; `AuthService.register`, `verify_email`, `login`, `_create_email_verification`; auth endpoints; `OAuthService._resolve_profile`; `StaffService.create_member` |

Supporting documents:

- `ypgym-state-transition-tables.md` — verified transition table for each required domain.
- `ypgym-state-transition-audit.md` — state inventory, mismatch report, guards and unresolved limitations.
- `generate_state_transition_drawio.py` — deterministic native Draw.io generator for this package.

