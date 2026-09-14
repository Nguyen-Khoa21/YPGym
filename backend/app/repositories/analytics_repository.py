from datetime import datetime

from sqlalchemy import Date, cast, distinct, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceEvent, AttendanceSession
from app.models.billing import Payment
from app.models.classes import ClassBooking, GymClass
from app.models.membership import UserMembership


class AnalyticsRepository:
    """Read-only aggregate queries used by manager analytics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def membership_trends(self, *, date_from: datetime, date_to: datetime):
        period = cast(func.date_trunc("month", func.timezone("UTC", UserMembership.created_at)), Date).label("period")
        result = await self.session.execute(
            select(
                period,
                func.count(UserMembership.id).filter(UserMembership.status == "active"),
                func.count(UserMembership.id).filter(UserMembership.status == "expiring_soon"),
                func.count(UserMembership.id).filter(UserMembership.status == "frozen"),
                func.count(UserMembership.id).filter(UserMembership.status == "expired"),
                func.count(UserMembership.id).filter(UserMembership.status == "cancelled"),
                func.count(UserMembership.id).filter(UserMembership.status == "revoked"),
                func.count(UserMembership.id).filter(UserMembership.status == "pending_verification"),
                func.count(UserMembership.id),
            )
            .where(UserMembership.created_at >= date_from, UserMembership.created_at <= date_to)
            .group_by(period)
            .order_by(period),
        )
        return result.all()

    async def class_popularity(self, *, date_from: datetime, date_to: datetime):
        included = (
            select(GymClass.id, GymClass.class_type, GymClass.capacity)
            .where(GymClass.start_at >= date_from, GymClass.start_at <= date_to, GymClass.status != "cancelled")
            .cte("included_classes")
        )
        capacities = (
            select(included.c.class_type, func.count().label("classes"), func.sum(included.c.capacity).label("capacity"))
            .group_by(included.c.class_type).subquery()
        )
        booking_summary = (
            select(
                included.c.class_type,
                func.count(ClassBooking.id).label("bookings"),
                func.count(distinct(ClassBooking.user_id)).label("members"),
            )
            .join(included, included.c.id == ClassBooking.class_id)
            .where(ClassBooking.status == "booked")
            .group_by(included.c.class_type)
            .subquery()
        )
        result = await self.session.execute(
            select(
                capacities.c.class_type,
                capacities.c.classes,
                func.coalesce(booking_summary.c.bookings, 0),
                func.coalesce(booking_summary.c.members, 0),
                capacities.c.capacity,
            )
            .select_from(capacities)
            .outerjoin(booking_summary, booking_summary.c.class_type == capacities.c.class_type)
            .order_by(func.coalesce(booking_summary.c.bookings, 0).desc(), capacities.c.class_type)
            .limit(10),
        )
        return result.all()

    async def attendance_summary(self, *, date_from: datetime, date_to: datetime):
        duration_minutes = extract(
            "epoch",
            AttendanceSession.closed_at - AttendanceSession.checked_in_at,
        ) / 60
        result = await self.session.execute(
            select(
                func.count(AttendanceEvent.id),
                func.count(distinct(AttendanceEvent.user_id)),
                func.avg(duration_minutes).filter(AttendanceSession.closed_at.is_not(None)),
            )
            .select_from(AttendanceEvent)
            .join(AttendanceSession, AttendanceSession.id == AttendanceEvent.session_id)
            .where(
                AttendanceEvent.event_type == "check_in",
                AttendanceEvent.event_at >= date_from,
                AttendanceEvent.event_at <= date_to,
            ),
        )
        return result.one()

    async def revenue_summary(self, *, date_from: datetime, date_to: datetime):
        result = await self.session.execute(
            select(
                func.count(Payment.id),
                func.coalesce(func.sum(Payment.amount), 0),
                func.coalesce(func.sum(Payment.discount_amount), 0),
            ).where(
                Payment.status == "succeeded",
                Payment.created_at >= date_from,
                Payment.created_at <= date_to,
            ),
        )
        return result.one()
