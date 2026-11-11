from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ResourceNotFoundError
from app.models.enums import ClassBookingStatus, PaymentStatus
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.billing_repository import PaymentRepository
from app.repositories.class_repository import ClassRepository
from app.schemas.payment_schema import PaymentStatusResponse
from app.services.state_transitions import transition_booking, transition_payment
from app.services.waitlist_service import WaitlistPromotionService


class PaymentStatusService:
    """Reads payment state and expires pending payments (and the class holds they carry)."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.payments = PaymentRepository(session)
        self.classes = ClassRepository(session)
        self.audit = AuditRepository(session)
        self.waitlist_promotions = WaitlistPromotionService(session, settings or get_settings())

    async def get_status(self, *, user: User, payment_id: UUID) -> PaymentStatusResponse:
        payment = await self.payments.get_for_user(payment_id=payment_id, user_id=user.id, for_update=True)
        if not payment:
            raise ResourceNotFoundError("Payment was not found.")
        await self._expire_payment_if_due(payment, datetime.now(UTC))
        return self.status_response(payment)

    async def get_status_by_order_code(self, *, user: User, order_code: int) -> PaymentStatusResponse:
        payment = await self.payments.get_by_payos_order_code(order_code, for_update=True)
        if not payment or payment.user_id != user.id:
            raise ResourceNotFoundError("Payment was not found.")
        await self._expire_payment_if_due(payment, datetime.now(UTC))
        return self.status_response(payment)

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
        await self.audit_expiry(payment)
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

    async def audit_expiry(self, payment) -> None:
        await self.audit.create(
            target_user_id=payment.user_id,
            action="payment.payos.expired",
            entity_type="payment",
            entity_id=str(payment.id),
            outcome="expired",
            summary="A pending payOS payment expired before confirmation.",
            after_data={"product_type": payment.product_type},
        )

    @staticmethod
    def status_response(payment) -> PaymentStatusResponse:
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
