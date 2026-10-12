import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ResourceNotFoundError
from app.models.enums import PaymentStatus
from app.models.user import User
from app.repositories.billing_repository import InvoiceRepository, PaymentRepository
from app.repositories.class_repository import ClassRepository
from app.repositories.email_delivery_repository import EmailDeliveryRepository
from app.repositories.membership_repository import MembershipPlanRepository
from app.repositories.operations_repository import AuditRepository, NotificationRepository
from app.schemas.class_schema import ClassCheckoutRequest, ClassCheckoutResponse
from app.schemas.payment_schema import PaymentStatusResponse, VNPayCreateRequest, VNPayCreateResponse
from app.services.invoice_service import InvoicePdfService
from app.services.membership_service import MembershipService
from app.services.vnpay_service import VNPaySigner


class VNPayPaymentService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.payments = PaymentRepository(session)
        self.plans = MembershipPlanRepository(session)
        self.memberships = MembershipService(session, self.settings)
        self.classes = ClassRepository(session)
        self.invoices = InvoiceRepository(session)
        self.invoice_pdf = InvoicePdfService()
        self.email_deliveries = EmailDeliveryRepository(session)
        self.notifications = NotificationRepository(session)
        self.audit = AuditRepository(session)

    def _signer(self) -> VNPaySigner:
        if not self.settings.vnpay_enabled:
            raise AppError("VNPAY_DISABLED", "VNPay payment is not configured.", 503)
        return VNPaySigner(self.settings.VNPAY_HASH_SECRET.get_secret_value())

    @staticmethod
    def _txn_ref(now: datetime) -> str:
        return f"{now.astimezone(ZoneInfo('Asia/Ho_Chi_Minh')):%y%m%d}{secrets.token_hex(10).upper()}"

    def _payment_url(self, *, payment, locale: str, bank_code: str | None, client_ip: str, label: str) -> str:
        now = payment.created_at or datetime.now(UTC)
        local_now = now.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        parameters: dict[str, str | int] = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": self.settings.VNPAY_TMN_CODE,
            "vnp_Amount": payment.amount_vnd * 100,
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": payment.txn_ref,
            "vnp_OrderInfo": f"YPGym {label} {payment.txn_ref}",
            "vnp_OrderType": "other",
            "vnp_Locale": locale,
            "vnp_ReturnUrl": self.settings.VNPAY_RETURN_URL,
            "vnp_IpAddr": client_ip or "127.0.0.1",
            "vnp_CreateDate": local_now.strftime("%Y%m%d%H%M%S"),
            "vnp_ExpireDate": payment.expires_at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y%m%d%H%M%S"),
        }
        if bank_code:
            parameters["vnp_BankCode"] = bank_code
        return self._signer().build_payment_url(self.settings.VNPAY_PAYMENT_URL, parameters)

    async def create_payment(self, *, user: User, payload: VNPayCreateRequest, client_ip: str) -> VNPayCreateResponse:
        self._signer()
        await self.memberships.validate_self_service_eligibility(user)
        plan = await self.plans.get_by_id(payload.membership_plan_id)
        if not plan or not plan.is_active:
            raise ResourceNotFoundError("Membership plan was not found.")
        current_membership = await self.memberships.memberships.get_current_for_user(user.id)
        quote = await self.memberships.attendance_benefit_quote(
            user=user,
            plan=plan,
            current_membership=current_membership,
        )
        if quote.status == "pending":
            raise AppError(
                "ATTENDANCE_BENEFIT_PENDING",
                "A discounted renewal checkout is already pending. Complete it or wait for it to expire.",
                409,
            )
        discount_amount = quote.pricing.discount_amount
        final_amount = quote.pricing.final_amount
        integral_amount = final_amount.to_integral_value()
        if final_amount != integral_amount or integral_amount <= 0:
            raise AppError("INVALID_PLAN_PRICE", "The selected plan has an invalid VND price.", 409)
        now = datetime.now(UTC)
        try:
            payment = await self.payments.create(
                user_id=user.id,
                membership_id=current_membership.id if quote.pricing.transaction_kind == "renewal" else None,
                plan_id=plan.id,
                product_type="membership",
                idempotency_key=f"vnpay:{self._txn_ref(now)}",
                amount=final_amount,
                amount_vnd=int(integral_amount),
                discount_amount=discount_amount,
                status=PaymentStatus.PENDING.value,
                mock_reference="",
                provider="vnpay",
                txn_ref=None,
                expires_at=now + timedelta(minutes=self.settings.VNPAY_TRANSACTION_TTL_MINUTES),
                client_platform=payload.client_platform,
                attendance_benefit_period_start=quote.period_start if quote.available else None,
                discount_details=quote.model_dump(mode="json"),
            )
        except IntegrityError as exc:
            await self.session.rollback()
            if quote.available:
                raise AppError(
                    "ATTENDANCE_BENEFIT_ALREADY_USED",
                    "This attendance benefit is already reserved or consumed.",
                    409,
                ) from exc
            raise
        payment.txn_ref = payment.idempotency_key.removeprefix("vnpay:")
        payment.mock_reference = payment.txn_ref
        await self._commit_payment()
        return VNPayCreateResponse(
            transaction_id=payment.id,
            txn_ref=payment.txn_ref,
            payment_url=self._payment_url(
                payment=payment,
                locale=payload.locale,
                bank_code=payload.bank_code,
                client_ip=client_ip,
                label="membership",
            ),
            expires_at=payment.expires_at,
        )

    async def create_class_payment(
        self,
        *,
        class_id: UUID,
        user: User,
        payload: ClassCheckoutRequest,
        client_ip: str,
    ) -> ClassCheckoutResponse:
        self._signer()
        if not user.is_email_verified:
            raise AppError("EMAIL_NOT_VERIFIED", "Please verify your email before booking a class.", 403)
        idempotency_key = f"class:{payload.idempotency_key}"
        existing = await self.payments.get_by_idempotency_key(user_id=user.id, idempotency_key=idempotency_key)
        if existing:
            if existing.product_type != "class_booking" or existing.class_booking.class_id != class_id:
                raise AppError("IDEMPOTENCY_KEY_REUSED", "Use a new checkout key for this class.", 409)
            return self._class_checkout_response(existing, payload, client_ip)

        now = datetime.now(UTC)
        gym_class = await self.classes.get_class(class_id, for_update=True)
        if not gym_class:
            raise ResourceNotFoundError("Class was not found.")
        if gym_class.status != "scheduled" or gym_class.start_at <= now:
            raise AppError("CLASS_UNAVAILABLE", "Only future scheduled classes can be purchased.", 409)
        if not gym_class.price_vnd or gym_class.price_vnd <= 0:
            raise AppError("CLASS_PRICE_NOT_SET", "This class is not available for paid checkout.", 409)

        expired = await self.classes.expire_holds_for_class(class_id, now)
        for item in expired:
            if item.current_payment and item.current_payment.status == PaymentStatus.PENDING.value:
                item.current_payment.status = PaymentStatus.EXPIRED.value
        booking = await self.classes.get_booking_for_user(class_id=class_id, user_id=user.id, for_update=True)
        has_active_hold = bool(
            booking
            and booking.status == "pending_payment"
            and booking.reserved_until
            and booking.reserved_until > now
        )
        if booking and booking.status == "confirmed":
            raise AppError("BOOKING_EXISTS", "You already have a confirmed booking for this class.", 409)
        if booking and booking.refund_status == "required":
            raise AppError("REFUND_REVIEW_REQUIRED", "Staff must resolve the previous paid cancellation first.", 409)
        if has_active_hold and booking.current_payment_id:
            raise AppError("CLASS_CHECKOUT_PENDING", "A payment is already pending for this seat.", 409)
        if not has_active_hold and await self.classes.occupied_booking_count(class_id) >= gym_class.capacity:
            raise AppError("CLASS_FULL", "This class is full. Join the waitlist instead.", 409)

        reserved_until = min(
            now + timedelta(minutes=self.settings.VNPAY_TRANSACTION_TTL_MINUTES),
            gym_class.start_at,
        )
        if booking:
            booking.status = "pending_payment"
            booking.price_vnd = gym_class.price_vnd
            booking.entitlement_source = "paid"
            booking.reserved_until = reserved_until
            booking.confirmed_at = None
            booking.cancelled_at = None
            booking.cancellation_reason = None
            booking.refund_status = "none"
        else:
            booking = await self.classes.create_booking(
                class_id=class_id,
                user_id=user.id,
                status="pending_payment",
                price_vnd=gym_class.price_vnd,
                entitlement_source="paid",
                reserved_until=reserved_until,
            )
        txn_ref = self._txn_ref(now)
        payment = await self.payments.create(
            user_id=user.id,
            membership_id=None,
            plan_id=None,
            class_booking_id=booking.id,
            product_type="class_booking",
            idempotency_key=idempotency_key,
            amount=Decimal(gym_class.price_vnd),
            amount_vnd=gym_class.price_vnd,
            discount_amount=Decimal("0"),
            status=PaymentStatus.PENDING.value,
            mock_reference=txn_ref,
            provider="vnpay",
            txn_ref=txn_ref,
            expires_at=reserved_until,
            client_platform=payload.client_platform,
        )
        booking.current_payment_id = payment.id
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError("DUPLICATE_PAYMENT_REQUEST", "This checkout request has already been processed.", 409) from exc
        payment.class_booking = booking
        booking.gym_class = gym_class
        return self._class_checkout_response(payment, payload, client_ip)

    def _class_checkout_response(self, payment, payload: ClassCheckoutRequest, client_ip: str) -> ClassCheckoutResponse:
        return ClassCheckoutResponse(
            booking_id=payment.class_booking_id,
            transaction_id=payment.id,
            txn_ref=payment.txn_ref,
            payment_url=self._payment_url(
                payment=payment,
                locale=payload.locale,
                bank_code=payload.bank_code,
                client_ip=client_ip,
                label="class",
            ),
            expires_at=payment.expires_at,
        )

    async def process_ipn(self, raw_parameters: dict[str, str]) -> dict[str, str]:
        signer = self._signer()
        parameters = signer.expected_response(raw_parameters)
        if not signer.validate(parameters):
            return {"RspCode": "97", "Message": "Invalid signature"}
        payment = await self.payments.get_by_txn_ref(parameters.get("vnp_TxnRef", ""), for_update=True)
        if not payment:
            return {"RspCode": "01", "Message": "Order not found"}
        if parameters.get("vnp_TmnCode") != self.settings.VNPAY_TMN_CODE:
            return {"RspCode": "97", "Message": "Invalid signature"}
        try:
            protocol_amount = int(parameters.get("vnp_Amount", ""))
        except ValueError:
            return {"RspCode": "04", "Message": "Invalid amount"}
        if protocol_amount != payment.amount_vnd * 100:
            return {"RspCode": "04", "Message": "Invalid amount"}
        response_code = parameters.get("vnp_ResponseCode", "")
        transaction_status = parameters.get("vnp_TransactionStatus", "")
        late_class_success = (
            payment.product_type == "class_booking"
            and payment.status in {
                PaymentStatus.EXPIRED.value,
                PaymentStatus.CANCELLED.value,
                PaymentStatus.FAILED.value,
            }
            and response_code == "00"
            and transaction_status == "00"
        )
        if payment.status != PaymentStatus.PENDING.value and not late_class_success:
            return {"RspCode": "02", "Message": "Order already confirmed"}

        payment.response_code = response_code
        payment.transaction_status = transaction_status
        payment.provider_transaction_no = parameters.get("vnp_TransactionNo") or None
        payment.bank_code = parameters.get("vnp_BankCode") or None
        payment.card_type = parameters.get("vnp_CardType") or None
        try:
            payment.pay_date = signer.parse_pay_date(parameters.get("vnp_PayDate"))
        except ValueError:
            await self.session.rollback()
            return {"RspCode": "99", "Message": "Unknown error"}
        now = datetime.now(UTC)
        if response_code == "00" and transaction_status == "00":
            user = (
                await self.session.execute(select(User).where(User.id == payment.user_id).with_for_update())
            ).scalar_one()
            payment.paid_at = payment.pay_date or now
            if payment.product_type == "membership" and payment.plan_id and not payment.class_booking_id:
                payment.status = PaymentStatus.PAID.value
                await self.memberships.finalize_vnpay_payment(
                    user=user, plan=payment.plan, payment=payment, transaction_date=payment.paid_at
                )
            elif payment.product_type == "class_booking" and payment.class_booking_id and not payment.plan_id:
                await self._finalize_class_payment(payment=payment, user=user, now=now)
            else:
                await self.session.rollback()
                return {"RspCode": "99", "Message": "Unknown error"}
        else:
            payment.status = PaymentStatus.CANCELLED.value if response_code == "24" else PaymentStatus.FAILED.value
            if payment.product_type == "class_booking" and payment.class_booking_id:
                booking = await self.classes.get_booking(payment.class_booking_id, for_update=True)
                if booking and booking.current_payment_id == payment.id and booking.status == "pending_payment":
                    booking.status = "payment_failed"
                    booking.reserved_until = None
            await self.audit.create(
                target_user_id=payment.user_id,
                action=f"payment.vnpay.{payment.status}",
                entity_type="payment",
                entity_id=str(payment.id),
                outcome=payment.status,
                summary="A verified VNPay IPN reported a non-successful payment outcome.",
                after_data={"provider": "vnpay", "product_type": payment.product_type, "response_code": response_code},
            )
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            return {"RspCode": "99", "Message": "Unknown error"}
        return {"RspCode": "00", "Message": "Confirm Success"}

    async def _finalize_class_payment(self, *, payment, user: User, now: datetime) -> None:
        booking = await self.classes.get_booking(payment.class_booking_id, for_update=True)
        if not booking:
            raise ResourceNotFoundError("Class booking was not found.")
        gym_class = await self.classes.get_class(booking.class_id, for_update=True)
        valid_hold = (
            booking.current_payment_id == payment.id
            and booking.status == "pending_payment"
            and booking.reserved_until is not None
            and booking.reserved_until >= now
            and gym_class is not None
            and gym_class.status == "scheduled"
            and gym_class.start_at > now
            and await self.classes.confirmed_booking_count(gym_class.id) < gym_class.capacity
        )
        if not valid_hold:
            payment.status = PaymentStatus.PAID_REVIEW.value
            if booking.status == "pending_payment":
                booking.status = "expired"
                booking.reserved_until = None
            booking.refund_status = "required"
            await self.audit.create(
                target_user_id=user.id,
                action="payment.vnpay.class_resolution_required",
                entity_type="payment",
                entity_id=str(payment.id),
                outcome="paid_review",
                summary="VNPay reported successful class payment after the reservation could no longer be fulfilled.",
                after_data={"class_booking_id": str(booking.id)},
            )
            return

        payment.status = PaymentStatus.PAID.value
        booking.status = "confirmed"
        booking.confirmed_at = payment.paid_at
        booking.reserved_until = None
        invoice_number = self.invoice_pdf.build_invoice_number(payment.id, payment.paid_at)
        pdf_path = self.invoice_pdf.generate_pdf(
            invoice_number=invoice_number,
            member_name=user.name,
            member_email=user.email,
            plan_name=gym_class.title,
            product_type="class_booking",
            product_name=gym_class.title,
            amount=payment.amount,
            discount_amount=payment.discount_amount,
            transaction_date=payment.paid_at,
            membership_start_date=None,
            membership_expiry_date=None,
            service_start_at=gym_class.start_at,
            service_end_at=gym_class.end_at,
        )
        invoice = await self.invoices.create(
            invoice_number=invoice_number,
            user_id=user.id,
            payment_id=payment.id,
            plan_name=gym_class.title,
            product_type="class_booking",
            product_name=gym_class.title,
            class_booking_id=booking.id,
            amount=payment.amount,
            discount_amount=payment.discount_amount,
            transaction_date=payment.paid_at,
            membership_start_date=None,
            membership_expiry_date=None,
            service_start_at=gym_class.start_at,
            service_end_at=gym_class.end_at,
            pdf_path=pdf_path,
        )
        recipient = user.email.lower()
        local, domain = recipient.rsplit("@", 1)
        masked = f"{local[:1]}{'*' * max(2, len(local) - 1)}@{domain}"
        for template_type in ("class_booking_confirmation", "class_booking_invoice"):
            await self.email_deliveries.enqueue_once(
                idempotency_key=f"{template_type}:{invoice.id}:{recipient}:v1",
                template_type=template_type,
                template_version=1,
                user_id=user.id,
                membership_id=None,
                class_booking_id=booking.id,
                payment_id=payment.id,
                invoice_id=invoice.id,
                recipient_email=recipient,
                recipient_masked=masked,
                status="queued",
            )
        await self.notifications.create_notification_once(
            user_id=user.id,
            category="class_booking",
            notification_type="class_payment_confirmed",
            title="Class booking confirmed",
            message=f"Your seat for {gym_class.title} is confirmed and invoice {invoice_number} is ready.",
            channel="in_app",
            delivery_state="delivered",
            delivered_at=payment.paid_at,
            dedupe_key=f"vnpay-class-payment:{payment.id}:in_app",
            action_type="class_booking",
            action_id=booking.id,
        )
        await self.audit.create(
            target_user_id=user.id,
            action="payment.vnpay.class_confirmed",
            entity_type="payment",
            entity_id=str(payment.id),
            outcome="paid",
            summary="A verified VNPay IPN confirmed one class reservation.",
            after_data={"class_booking_id": str(booking.id), "invoice_id": str(invoice.id)},
        )

    async def return_redirect(self, raw_parameters: dict[str, str]) -> str:
        signer = self._signer()
        parameters = signer.expected_response(raw_parameters)
        if not signer.validate(parameters):
            return self._result_url(self.settings.FRONTEND_PAYMENT_RESULT_URL, state="invalid")
        payment = await self.payments.get_by_txn_ref(parameters.get("vnp_TxnRef", ""))
        if not payment:
            return self._result_url(self.settings.FRONTEND_PAYMENT_RESULT_URL, state="invalid")
        if payment.client_platform == "mobile":
            target = self.settings.MOBILE_PAYMENT_RESULT_URL
        elif payment.client_platform == "mobile_web":
            target = f"{self.settings.MOBILE_WEB_URL.rstrip('/')}/payment-result"
        else:
            target = self.settings.FRONTEND_PAYMENT_RESULT_URL
        if payment.status == PaymentStatus.PAID.value:
            state = "success"
        elif payment.status == PaymentStatus.PAID_REVIEW.value:
            state = "review"
        elif parameters.get("vnp_ResponseCode") == "24":
            state = "cancelled"
        elif parameters.get("vnp_ResponseCode") != "00" or parameters.get("vnp_TransactionStatus") != "00":
            state = "failed"
        else:
            state = "processing"
        return self._result_url(target, transaction_id=str(payment.id), state=state)

    async def get_status(self, *, user: User, payment_id: UUID) -> PaymentStatusResponse:
        payment = await self.payments.get_for_user(payment_id=payment_id, user_id=user.id, for_update=True)
        if not payment:
            raise ResourceNotFoundError("Payment was not found.")
        await self._expire_payment_if_due(payment, datetime.now(UTC))
        return self._status_response(payment)

    async def expire_pending(self) -> int:
        payments = await self.payments.list_expired_pending_for_update(datetime.now(UTC))
        for payment in payments:
            await self._expire_payment_if_due(payment, datetime.now(UTC), commit=False)
        await self.session.commit()
        return len(payments)

    async def _expire_payment_if_due(self, payment, now: datetime, *, commit: bool = True) -> None:
        if payment.status != PaymentStatus.PENDING.value or not payment.expires_at or payment.expires_at > now:
            return
        payment.status = PaymentStatus.EXPIRED.value
        if payment.product_type == "class_booking" and payment.class_booking_id:
            booking = await self.classes.get_booking(payment.class_booking_id, for_update=True)
            if booking and booking.current_payment_id == payment.id and booking.status == "pending_payment":
                booking.status = "expired"
                booking.reserved_until = None
        await self.audit.create(
            target_user_id=payment.user_id,
            action="payment.vnpay.expired",
            entity_type="payment",
            entity_id=str(payment.id),
            outcome="expired",
            summary="A pending VNPay payment expired before confirmation.",
            after_data={"product_type": payment.product_type},
        )
        if commit:
            await self.session.commit()

    async def resolve_class_refund(self, *, payment_id: UUID, actor: User, reason: str) -> PaymentStatusResponse:
        payment = await self.payments.get_by_id(payment_id, for_update=True)
        if not payment or payment.product_type != "class_booking" or not payment.class_booking_id:
            raise ResourceNotFoundError("Class payment was not found.")
        booking = await self.classes.get_booking(payment.class_booking_id, for_update=True)
        if not booking or booking.refund_status != "required":
            raise AppError("REFUND_NOT_REQUIRED", "This class payment does not require refund resolution.", 409)
        booking.refund_status = "resolved"
        booking.status = "refunded"
        await self.audit.create(
            actor_user_id=actor.id,
            target_user_id=payment.user_id,
            action="payment.vnpay.class_refund_resolved",
            entity_type="payment",
            entity_id=str(payment.id),
            reason=reason.strip(),
            outcome="resolved",
            summary="Staff recorded manual resolution of a paid class exception.",
            after_data={"class_booking_id": str(booking.id)},
        )
        await self.session.commit()
        payment = await self.payments.get_by_id(payment.id)
        return self._status_response(payment)

    async def _commit_payment(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError("PAYMENT_REFERENCE_CONFLICT", "Please start the payment again.", 409) from exc

    @staticmethod
    def _result_url(base_url: str, **values: str) -> str:
        parts = urlsplit(base_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.update(values)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    @staticmethod
    def _status_response(payment) -> PaymentStatusResponse:
        membership = payment.membership
        booking = payment.class_booking
        gym_class = booking.gym_class if booking else None
        invoice = payment.invoice
        product_name = payment.plan.name if payment.plan else gym_class.title
        return PaymentStatusResponse(
            id=payment.id,
            product_type=payment.product_type,
            membership_plan_id=payment.plan_id,
            class_booking_id=payment.class_booking_id,
            product_name=product_name,
            plan_name=payment.plan.name if payment.plan else None,
            provider=payment.provider,
            txn_ref=payment.txn_ref or payment.mock_reference,
            status=payment.status,
            amount_vnd=payment.amount_vnd,
            currency=payment.currency,
            membership_status=membership.status if membership else None,
            membership_start_date=membership.start_date if membership else None,
            membership_expiry_date=membership.expiry_date if membership else None,
            booking_status=booking.status if booking else None,
            refund_status=booking.refund_status if booking else None,
            class_start_at=gym_class.start_at if gym_class else None,
            class_end_at=gym_class.end_at if gym_class else None,
            invoice_id=invoice.id if invoice else None,
            invoice_download_url=f"/api/v1/billing/me/invoices/{invoice.id}" if invoice else None,
            created_at=payment.created_at,
            paid_at=payment.paid_at,
            expires_at=payment.expires_at,
            discount_details=payment.discount_details,
        )
