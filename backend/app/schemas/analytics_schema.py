from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.attendance_schema import CrowdednessResponse


class MembershipTrendPoint(BaseModel):
    period: date
    active: int = 0
    expiring_soon: int = 0
    frozen: int = 0
    expired: int = 0
    cancelled: int = 0
    revoked: int = 0
    pending_verification: int = 0
    total: int = 0


class ClassPopularityPoint(BaseModel):
    class_type: str
    class_count: int
    bookings: int
    unique_members: int
    capacity: int
    utilization_percent: float = Field(ge=0)


class AttendanceAnalyticsSummary(BaseModel):
    check_ins: int
    unique_members: int
    average_visit_minutes: float | None
    busiest_slot: str | None
    current_occupancy: CrowdednessResponse


class RevenueAnalyticsSummary(BaseModel):
    successful_payments: int
    gross_amount: Decimal
    discounts: Decimal


class AnalyticsSummaryResponse(BaseModel):
    date_from: datetime
    date_to: datetime
    generated_at: datetime
    cache_hit: bool = False
    cache_ttl_seconds: int = 60
    membership_trends: list[MembershipTrendPoint]
    class_popularity: list[ClassPopularityPoint]
    attendance: AttendanceAnalyticsSummary
    revenue: RevenueAnalyticsSummary
