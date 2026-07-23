from datetime import UTC, date, datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.dashboard_schema import (
    DashboardMember,
    DashboardMembership,
    DashboardQrAccess,
    DashboardQuickAction,
    MemberDashboard,
)
from app.services.attendance_service import CrowdednessService
from app.services.class_service import BookingService
from app.services.lifecycle_service import MembershipLifecycleService
from app.services.notification_service import NotificationService


class DashboardService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.lifecycle = MembershipLifecycleService(session)
        self.bookings = BookingService(session, redis)
        self.notifications = NotificationService(session)
        self.crowdedness = CrowdednessService(session, redis)

    async def get(self, user: User) -> MemberDashboard:
        membership, status, eligible, reason = await self.lifecycle.access_snapshot(user)
        booking_state = await self.bookings.list_my(user)
        recent_notifications, unread_notification_count = await self.notifications.list_recent_unread(
            user=user,
            limit=3,
        )
        broadcasts = await self.notifications.list_active_broadcasts(user)
        now = datetime.now(UTC)
        upcoming = sorted(
            (
                item
                for item in booking_state.bookings
                if item.status == "booked"
                and item.gym_class.status == "scheduled"
                and item.gym_class.start_at > now
            ),
            key=lambda item: item.gym_class.start_at,
        )[:3]
        waitlists = sorted(
            (
                item
                for item in booking_state.waitlists
                if item.status == "waiting" and item.gym_class.start_at > now
            ),
            key=lambda item: item.gym_class.start_at,
        )[:3]
        days_remaining = max((membership.expiry_date - date.today()).days, 0) if membership else 0
        membership_summary = None
        if membership:
            membership_summary = DashboardMembership(
                id=membership.id,
                plan_name=membership.plan.name,
                status=status,
                start_date=membership.start_date,
                expiry_date=membership.expiry_date,
                days_remaining=days_remaining,
                message=f"{days_remaining} days remaining." if eligible else (reason or "Membership access is unavailable."),
            )
        membership_action = "Renew membership" if membership else "Buy membership"
        return MemberDashboard(
            member=DashboardMember(id=user.id, name=user.name, tier=user.tier),
            membership=membership_summary,
            qr_access=DashboardQrAccess(eligible=eligible, reason=reason),
            crowdedness=await self.crowdedness.get(),
            upcoming_bookings=upcoming,
            active_waitlists=waitlists,
            unread_notification_count=unread_notification_count,
            recent_notifications=recent_notifications,
            active_broadcasts=broadcasts[:3],
            quick_actions=[
                DashboardQuickAction(key="membership", label=membership_action, target="/memberships", enabled=True),
                DashboardQuickAction(key="qr", label="QR code", target="/app/qr", enabled=eligible, reason=reason),
                DashboardQuickAction(key="classes", label="Classes", target="/app/classes", enabled=True),
                DashboardQuickAction(key="profile", label="Profile", target="/app/profile", enabled=True),
            ],
        )
