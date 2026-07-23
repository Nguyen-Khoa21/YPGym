from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.attendance_schema import CrowdednessResponse
from app.schemas.class_schema import BookingItem, WaitlistItem
from app.schemas.notification_schema import BroadcastItem, NotificationItem


class DashboardMember(BaseModel):
    id: UUID
    name: str
    tier: str


class DashboardMembership(BaseModel):
    id: UUID
    plan_name: str
    status: str
    start_date: date
    expiry_date: date
    days_remaining: int
    message: str


class DashboardQrAccess(BaseModel):
    eligible: bool
    reason: str | None
    target: str = "/app/qr"


class DashboardQuickAction(BaseModel):
    key: str
    label: str
    target: str
    enabled: bool
    reason: str | None = None


class MemberDashboard(BaseModel):
    member: DashboardMember
    membership: DashboardMembership | None
    qr_access: DashboardQrAccess
    crowdedness: CrowdednessResponse
    upcoming_bookings: list[BookingItem]
    active_waitlists: list[WaitlistItem]
    unread_notification_count: int
    recent_notifications: list[NotificationItem]
    active_broadcasts: list[BroadcastItem]
    quick_actions: list[DashboardQuickAction]
