from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ResourceNotFoundError
from app.models.enums import ClassBookingStatus, PaymentStatus, RefundStatus
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.billing_repository import InvoiceRepository, PaymentRepository
from app.repositories.class_repository import ClassRepository
from app.repositories.email_delivery_repository import EmailDeliveryRepository
from app.repositories.gym_repository import GymRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.class_schema import ClassCheckoutRequest, ClassCheckoutResponse
from app.schemas.payment_schema import PaymentStatusResponse
from app.services.invoice_service import InvoicePdfService
from app.services.payment_status_service import PaymentStatusService
from app.services.payos_service import require_payos_client
from app.services.state_transitions import transition_booking, transition_payment, transition_refund
from app.services.waitlist_service import WaitlistPromotionService


class ClassPaymentService:
    """Paid class checkout: seat holds, payOS settlement into a booking and invoice, and manual refund resolution."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.payments = PaymentRepository(session)
        self.classes = ClassRepository(session)
        self.gyms = GymRepository(session)
        self.invoices = InvoiceRepository(session)
        self.invoice_pdf = InvoicePdfService()
        self.email_deliveries = EmailDeliveryRepository(session)
        self.notifications = NotificationRepository(session)
        self.audit = AuditRepository(session)
        self.waitlist_promotions = WaitlistPromotionService(session, self.settings)
        self.status = PaymentStatusService(session, self.settings)

    async def create_class_payment(
        self,
        *,
        class_id: UUID,
        user: User,
        payload: ClassCheckoutRequest,
    ) -> ClassCheckoutResponse:
        client = require_payos_client(self.settings)
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
        if not await self.gyms.get_location(gym_class.gym_id, active_only=True):
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
                await self.status.audit_expiry(item.current_payment)
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
        await client.attach_payment_link(payment)
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

    async def finalize(self, *, payment, user: User, now: datetime) -> None:
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

    async def resolve_refund(self, *, payment_id: UUID, actor: User, reason: str) -> PaymentStatusResponse:
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
        return self.status.status_response(payment)
