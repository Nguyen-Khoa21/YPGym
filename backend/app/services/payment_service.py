from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ResourceNotFoundError
from app.models.enums import ClassBookingStatus, PaymentStatus, RefundStatus
from app.models.user import User
from app.repositories.billing_repository import InvoiceRepository, PaymentRepository
from app.repositories.class_repository import ClassRepository
from app.repositories.email_delivery_repository import EmailDeliveryRepository
from app.repositories.membership_repository import MembershipPlanRepository
from app.repositories.operations_repository import AuditRepository, NotificationRepository
from app.schemas.class_schema import ClassCheckoutRequest, ClassCheckoutResponse
from app.schemas.payment_schema import PaymentStatusResponse, PayOSCreateRequest, PayOSCreateResponse
from app.services.invoice_service import InvoicePdfService
from app.services.membership_service import MembershipService
from app.services.payos_service import PayOSClient
from app.services.state_transitions import transition_booking, transition_payment, transition_refund
from app.services.waitlist_service import WaitlistPromotionService


class PayOSPaymentService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        payos: PayOSClient | None = None,
    ) -> None:
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
        self.waitlist_promotions = WaitlistPromotionService(session, self.settings)
        self._payos = payos

    def _client(self) -> PayOSClient:
        if not self.settings.PAYOS_ENABLED:
            raise AppError("PAYOS_DISABLED", "payOS payment is not configured.", 503)
        if self._payos is None:
            self._payos = PayOSClient(self.settings)
        return self._payos

    @staticmethod
    def _description(order_code: int) -> str:
        return f"YPG{order_code % 1_000_000:06d}"

    async def _attach_payment_link(self, payment) -> str | None:
        response = await self._client().create_payment_link(
            order_code=payment.payos_order_code,
            amount=payment.amount_vnd,
            description=self._description(payment.payos_order_code),
            expired_at=int(payment.expires_at.timestamp()),
        )
        if response.order_code != payment.payos_order_code or response.amount != payment.amount_vnd:
            raise AppError("PAYOS_RESPONSE_MISMATCH", "The payment provider returned inconsistent checkout data.", 502)
        payment.payment_link_id = response.payment_link_id
        payment.checkout_url = response.checkout_url
        return getattr(response, "qr_code", None)

    async def create_payment(
        self,
        *,
        user: User,
        payload: PayOSCreateRequest,
        actor: User | None = None,
        idempotency_key: str | None = None,
    ) -> PayOSCreateResponse:
        """Create a pending payOS checkout. With `actor`, staff create it on behalf of `user` at the actor's gym."""
        self._client()
        stored_key = f"staff-qr:{idempotency_key}" if actor and idempotency_key else None
        if stored_key:
            existing = await self.payments.get_by_idempotency_key(user_id=user.id, idempotency_key=stored_key)
            if existing:
                if existing.plan_id != payload.membership_plan_id:
                    raise AppError(
                        "IDEMPOTENCY_KEY_REUSED",
                        "Use a new payment key when changing the membership plan.",
                        409,
                    )
                return PayOSCreateResponse(
                    transaction_id=existing.id,
                    order_code=existing.payos_order_code,
                    checkout_url=existing.checkout_url,
                    amount_vnd=existing.amount_vnd,
                    expires_at=existing.expires_at,
                    gym_id=existing.gym_id,
                    gym_name=existing.gym.name,
                )
        await self.memberships.validate_self_service_eligibility(user)
        plan = await self.plans.get_by_id(payload.membership_plan_id)
        if not plan or not plan.is_active:
            raise ResourceNotFoundError("Membership plan was not found.")
        gym = await self.memberships.resolve_purchase_gym(
            user=user,
            requested_gym_id=payload.gym_id,
            actor=actor,
        )
        current_membership = await self.memberships.memberships.get_current_for_user(user.id)
        quote = await self.memberships.attendance_benefit_quote(
            user=user,
            plan=plan,
            current_membership=current_membership,
            gym=gym,
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
        order_code = await self.payments.next_payos_order_code()
        try:
            payment = await self.payments.create(
                gym_id=gym.id,
                user_id=user.id,
                membership_id=current_membership.id if quote.pricing.transaction_kind == "renewal" else None,
                plan_id=plan.id,
                product_type="membership",
                idempotency_key=stored_key or f"payos:{order_code}",
                amount=final_amount,
                amount_vnd=int(integral_amount),
                discount_amount=discount_amount,
                status=PaymentStatus.PENDING.value,
                mock_reference=str(order_code),
                provider="payos",
                txn_ref=str(order_code),
                payos_order_code=order_code,
                expires_at=now + timedelta(minutes=self.settings.PAYOS_TRANSACTION_TTL_MINUTES),
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
        qr_code = await self._attach_payment_link(payment)
        await self._commit_payment()
        return PayOSCreateResponse(
            transaction_id=payment.id,
            order_code=payment.payos_order_code,
            checkout_url=payment.checkout_url,
            amount_vnd=payment.amount_vnd,
            expires_at=payment.expires_at,
            gym_id=gym.id,
            gym_name=gym.name,
            qr_code=qr_code,
        )

    async def create_class_payment(
        self,
        *,
        class_id: UUID,
        user: User,
        payload: ClassCheckoutRequest,
    ) -> ClassCheckoutResponse:
        self._client()
        if not user.is_email_verified:
            raise AppError("EMAIL_NOT_VERIFIED", "Please verify your email before booking a class.", 403)
        idempotency_key = f"class:{payload.idempotency_key}"
        existing = await self.payments.get_by_idempotency_key(user_id=user.id, idempotency_key=idempotency_key)
        if existing:
            if existing.product_type != "class_booking" or existing.class_booking.class_id != class_id:
                raise AppError("IDEMPOTENCY_KEY_REUSED", "Use a new checkout key for this class.", 409)
            return self._class_checkout_response(existing)

        now = datetime.now(UTC)
        gym_class = await self.classes.get_class(class_id, for_update=True)
        if not gym_class:
            raise ResourceNotFoundError("Class was not found.")
        if not await self.memberships.gyms.get_location(gym_class.gym_id, active_only=True):
            raise AppError("CLASS_GYM_INACTIVE", "This class's gym location is inactive.", 409)
        if gym_class.status != "scheduled" or gym_class.start_at <= now:
            raise AppError("CLASS_UNAVAILABLE", "Only future scheduled classes can be purchased.", 409)
        if not gym_class.price_vnd or gym_class.price_vnd <= 0:
            raise AppError("CLASS_PRICE_NOT_SET", "This class is not available for paid checkout.", 409)

        expired = await self.classes.expired_holds_for_class(class_id, now)
        for item in expired:
            transition_booking(item, ClassBookingStatus.EXPIRED)
            item.reserved_until = None
            if item.current_payment and item.current_payment.status == PaymentStatus.PENDING.value:
                transition_payment(item.current_payment, PaymentStatus.EXPIRED)
                await self._audit_payment_expiry(item.current_payment)
            await self.waitlist_promotions.promote(gym_class, now=now)
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
            if expired:
                await self.session.commit()
            raise AppError("CLASS_FULL", "This class is full. Join the waitlist instead.", 409)

        reserved_until = min(
            now + timedelta(minutes=self.settings.PAYOS_TRANSACTION_TTL_MINUTES),
            gym_class.start_at,
        )
        if booking:
            transition_booking(booking, ClassBookingStatus.PENDING_PAYMENT, idempotent=True)
            booking.price_vnd = gym_class.price_vnd
            booking.entitlement_source = "paid"
            booking.reserved_until = reserved_until
            booking.confirmed_at = None
            booking.cancelled_at = None
            booking.cancellation_reason = None
            transition_refund(booking, RefundStatus.NONE, idempotent=True)
        else:
            booking = await self.classes.create_booking(
                class_id=class_id,
                user_id=user.id,
                status="pending_payment",
                price_vnd=gym_class.price_vnd,
                entitlement_source="paid",
                reserved_until=reserved_until,
            )
        order_code = await self.payments.next_payos_order_code()
        payment = await self.payments.create(
            gym_id=gym_class.gym_id,
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
            mock_reference=str(order_code),
            provider="payos",
            txn_ref=str(order_code),
            payos_order_code=order_code,
            expires_at=reserved_until,
            client_platform=payload.client_platform,
        )
        booking.current_payment_id = payment.id
        await self._attach_payment_link(payment)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError("DUPLICATE_PAYMENT_REQUEST", "This checkout request has already been processed.", 409) from exc
        payment.class_booking = booking
        booking.gym_class = gym_class
        return self._class_checkout_response(payment)

    @staticmethod
    def _class_checkout_response(payment) -> ClassCheckoutResponse:
        return ClassCheckoutResponse(
            booking_id=payment.class_booking_id,
            transaction_id=payment.id,
            order_code=payment.payos_order_code,
            checkout_url=payment.checkout_url,
            amount_vnd=payment.amount_vnd,
            expires_at=payment.expires_at,
        )

    async def process_webhook(self, payload: bytes) -> dict[str, str]:
        data = await self._client().verify_webhook(payload)
        payment = await self.payments.get_by_payos_order_code(data.order_code, for_update=True)
        if not payment:
            return {"code": "00", "desc": "success"}
        if data.amount != payment.amount_vnd or data.currency != "VND":
            raise AppError("PAYOS_AMOUNT_MISMATCH", "The verified payment amount does not match the order.", 400)
        if payment.payment_link_id and data.payment_link_id != payment.payment_link_id:
            raise AppError("PAYOS_LINK_MISMATCH", "The verified payment link does not match the order.", 400)
        if data.code != "00":
            return {"code": "00", "desc": "success"}
        late_class_success = (
            payment.product_type == "class_booking"
            and payment.status in {
                PaymentStatus.EXPIRED.value,
                PaymentStatus.CANCELLED.value,
                PaymentStatus.FAILED.value,
            }
        )
        if payment.status in {PaymentStatus.PAID.value, PaymentStatus.PAID_REVIEW.value}:
            return {"code": "00", "desc": "success"}
        if payment.status != PaymentStatus.PENDING.value and not late_class_success:
            payment.provider_transaction_no = data.reference
            payment.paid_at = datetime.now(UTC)
            transition_payment(payment, PaymentStatus.PAID_REVIEW)
            await self.audit.create(
                target_user_id=payment.user_id,
                action="payment.payos.late_success",
                entity_type="payment",
                entity_id=str(payment.id),
                outcome="paid_review",
                summary="payOS reported payment after the local attempt reached a final state.",
                after_data={"provider": "payos", "product_type": payment.product_type},
            )
            await self.session.commit()
            return {"code": "00", "desc": "success"}

        payment.response_code = data.code
        payment.transaction_status = "PAID"
        payment.provider_transaction_no = data.reference
        payment.payment_link_id = data.payment_link_id
        try:
            payment.pay_date = datetime.strptime(data.transaction_date_time, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")
            )
        except ValueError:
            payment.pay_date = None
        now = datetime.now(UTC)
        user = (
            await self.session.execute(select(User).where(User.id == payment.user_id).with_for_update())
        ).scalar_one()
        payment.paid_at = payment.pay_date or now
        if payment.product_type == "membership" and payment.plan_id and not payment.class_booking_id:
            if not payment.gym.is_active:
                transition_payment(payment, PaymentStatus.PAID_REVIEW)
                await self.audit.create(
                    target_user_id=payment.user_id,
                    action="payment.payos.membership_resolution_required",
                    entity_type="payment",
                    entity_id=str(payment.id),
                    outcome="paid_review",
                    summary="The selected gym became inactive before membership payment settlement.",
                    after_data={"gym_id": str(payment.gym_id)},
                )
                await self.session.commit()
                return {"code": "00", "desc": "success"}
            transition_payment(payment, PaymentStatus.PAID)
            await self.memberships.finalize_provider_payment(
                user=user, plan=payment.plan, payment=payment, transaction_date=payment.paid_at
            )
        elif payment.product_type == "class_booking" and payment.class_booking_id and not payment.plan_id:
            await self._finalize_class_payment(payment=payment, user=user, now=now)
        else:
            raise AppError("PAYMENT_PRODUCT_INVALID", "The payment product mapping is invalid.", 409)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError("PAYOS_REFERENCE_CONFLICT", "The payment reference was already processed.", 409) from exc
        return {"code": "00", "desc": "success"}

    async def _finalize_class_payment(self, *, payment, user: User, now: datetime) -> None:
        linked_booking = payment.class_booking
        if not linked_booking:
            raise ResourceNotFoundError("Class booking was not found.")
        gym_class = await self.classes.get_class(linked_booking.class_id, for_update=True)
        booking = await self.classes.get_booking(payment.class_booking_id, for_update=True)
        if not booking:
            raise ResourceNotFoundError("Class booking was not found.")
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
            transition_payment(payment, PaymentStatus.PAID_REVIEW)
            released = False
            if booking.status == "pending_payment":
                transition_booking(booking, ClassBookingStatus.EXPIRED)
                booking.reserved_until = None
                released = True
            transition_refund(booking, RefundStatus.REQUIRED)
            if released and gym_class:
                await self.waitlist_promotions.promote(gym_class, now=now)
            await self.audit.create(
                target_user_id=user.id,
                action="payment.payos.class_resolution_required",
                entity_type="payment",
                entity_id=str(payment.id),
                outcome="paid_review",
                summary="payOS reported successful class payment after the reservation could no longer be fulfilled.",
                after_data={"class_booking_id": str(booking.id)},
            )
            return

        transition_payment(payment, PaymentStatus.PAID)
        transition_booking(booking, ClassBookingStatus.CONFIRMED)
        booking.confirmed_at = payment.paid_at
        booking.reserved_until = None
        invoice_number = self.invoice_pdf.build_invoice_number(payment.id, payment.paid_at)
        pdf_path = self.invoice_pdf.generate_pdf(
            invoice_number=invoice_number,
            member_name=user.name,
            member_email=user.email,
            plan_name=gym_class.title,
            product_type="class_booking",
            product_name=f"{gym_class.title} · {payment.gym.name}",
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
            product_name=f"{gym_class.title} · {payment.gym.name}",
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
            message=(
                f"Your seat for {gym_class.title} at {payment.gym.name} is confirmed and "
                f"invoice {invoice_number} is ready."
            ),
            channel="in_app",
            delivery_state="delivered",
            delivered_at=payment.paid_at,
            dedupe_key=f"payos-class-payment:{payment.id}:in_app",
            action_type="class_booking",
            action_id=booking.id,
        )
        await self.audit.create(
            target_user_id=user.id,
            action="payment.payos.class_confirmed",
            entity_type="payment",
            entity_id=str(payment.id),
            outcome="paid",
            summary="A verified payOS webhook confirmed one class reservation.",
            after_data={
                "class_booking_id": str(booking.id),
                "invoice_id": str(invoice.id),
                "gym_id": str(payment.gym_id),
            },
        )

    async def get_status(self, *, user: User, payment_id: UUID) -> PaymentStatusResponse:
        payment = await self.payments.get_for_user(payment_id=payment_id, user_id=user.id, for_update=True)
        if not payment:
            raise ResourceNotFoundError("Payment was not found.")
        await self._expire_payment_if_due(payment, datetime.now(UTC))
        return self._status_response(payment)

    async def get_status_by_order_code(self, *, user: User, order_code: int) -> PaymentStatusResponse:
        payment = await self.payments.get_by_payos_order_code(order_code, for_update=True)
        if not payment or payment.user_id != user.id:
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
        transition_payment(payment, PaymentStatus.EXPIRED)
        if payment.product_type == "class_booking" and payment.class_booking_id:
            await self._release_current_class_hold(
                payment=payment,
                target=ClassBookingStatus.EXPIRED,
                now=now,
            )
        await self._audit_payment_expiry(payment)
        if commit:
            await self.session.commit()

    async def _release_current_class_hold(
        self,
        *,
        payment,
        target: ClassBookingStatus,
        now: datetime,
    ) -> bool:
        linked_booking = payment.class_booking
        if not linked_booking:
            return False
        gym_class = await self.classes.get_class(linked_booking.class_id, for_update=True)
        booking = await self.classes.get_booking(payment.class_booking_id, for_update=True)
        if (
            not booking
            or booking.current_payment_id != payment.id
            or booking.status != ClassBookingStatus.PENDING_PAYMENT.value
        ):
            return False
        transition_booking(booking, target)
        booking.reserved_until = None
        if gym_class:
            await self.waitlist_promotions.promote(gym_class, now=now)
        return True

    async def _audit_payment_expiry(self, payment) -> None:
        await self.audit.create(
            target_user_id=payment.user_id,
            action="payment.payos.expired",
            entity_type="payment",
            entity_id=str(payment.id),
            outcome="expired",
            summary="A pending payOS payment expired before confirmation.",
            after_data={"product_type": payment.product_type},
        )

    async def resolve_class_refund(self, *, payment_id: UUID, actor: User, reason: str) -> PaymentStatusResponse:
        payment = await self.payments.get_by_id(payment_id, for_update=True)
        if not payment or payment.product_type != "class_booking" or not payment.class_booking_id:
            raise ResourceNotFoundError("Class payment was not found.")
        booking = await self.classes.get_booking(payment.class_booking_id, for_update=True)
        if not booking or booking.refund_status != "required":
            raise AppError("REFUND_NOT_REQUIRED", "This class payment does not require refund resolution.", 409)
        transition_refund(booking, RefundStatus.RESOLVED)
        transition_booking(booking, ClassBookingStatus.REFUNDED)
        await self.audit.create(
            actor_user_id=actor.id,
            target_user_id=payment.user_id,
            action="payment.payos.class_refund_resolved",
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
    def _status_response(payment) -> PaymentStatusResponse:
        membership = payment.membership
        booking = payment.class_booking
        gym_class = booking.gym_class if booking else None
        invoice = payment.invoice
        product_name = payment.plan.name if payment.plan else gym_class.title
        return PaymentStatusResponse(
            id=payment.id,
            gym_id=payment.gym_id,
            gym_name=payment.gym.name,
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
