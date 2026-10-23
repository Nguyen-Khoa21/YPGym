from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.classes import ClassBooking, GymClass
from app.models.enums import ClassBookingStatus, ClassStatus, RefundStatus, WaitlistStatus
from app.repositories.class_repository import ClassRepository
from app.services.notification_service import NotificationService
from app.services.state_transitions import transition_booking, transition_refund, transition_waitlist


class WaitlistPromotionService:
    """Promote one eligible waitlist entry while the caller holds the class row lock."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.classes = ClassRepository(session)
        self.notifications = NotificationService(session)
        self.settings = settings or get_settings()

    async def promote(self, gym_class: GymClass, *, now: datetime | None = None) -> ClassBooking | None:
        promotion_time = now or datetime.now(UTC)
        if gym_class.status != ClassStatus.SCHEDULED.value or gym_class.start_at <= promotion_time:
            return None
        if await self.classes.occupied_booking_count(gym_class.id) >= gym_class.capacity:
            return None
        for waitlist, user in await self.classes.waiting_entries_for_update(gym_class.id):
            if not user.is_email_verified:
                transition_waitlist(waitlist, WaitlistStatus.CANCELLED)
                continue
            booking = await self.classes.get_booking_for_user(
                class_id=gym_class.id,
                user_id=user.id,
                for_update=True,
            )
            if booking and booking.status in {
                ClassBookingStatus.CONFIRMED.value,
                ClassBookingStatus.PENDING_PAYMENT.value,
            }:
                transition_waitlist(waitlist, WaitlistStatus.CANCELLED)
                continue
            if booking and booking.refund_status == RefundStatus.REQUIRED.value:
                transition_waitlist(waitlist, WaitlistStatus.CANCELLED)
                continue
            reserved_until = min(
                promotion_time + timedelta(minutes=self.settings.VNPAY_TRANSACTION_TTL_MINUTES),
                gym_class.start_at,
            )
            if booking:
                transition_booking(booking, ClassBookingStatus.PENDING_PAYMENT)
                booking.price_vnd = gym_class.price_vnd
                booking.entitlement_source = "paid"
                booking.current_payment_id = None
                booking.reserved_until = reserved_until
                transition_refund(booking, RefundStatus.NONE, idempotent=True)
            else:
                booking = await self.classes.create_booking(
                    class_id=gym_class.id,
                    user_id=user.id,
                    status=ClassBookingStatus.PENDING_PAYMENT.value,
                    price_vnd=gym_class.price_vnd,
                    entitlement_source="paid",
                    reserved_until=reserved_until,
                )
            transition_waitlist(waitlist, WaitlistStatus.PROMOTED)
            await self.notifications.queue_class_promotion(
                user=user,
                class_id=gym_class.id,
                class_title=gym_class.title,
                class_start=gym_class.start_at,
                waitlist_id=waitlist.id,
                waitlist_position=waitlist.position,
            )
            return booking
        return None
