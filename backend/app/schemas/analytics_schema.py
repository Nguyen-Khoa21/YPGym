from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

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
    current_occupancy: CrowdednessResponse | None = None


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
    revenue: RevenueAnalyticsSummary | None = None
    gym_id: UUID | None = None


class TrafficWindowPoint(BaseModel):
    start_hour: int = Field(ge=0, le=22)
    end_hour: int = Field(ge=2, le=24)
    label: str
    average_headcount: float = Field(ge=0)
    average_capacity_percentage: float = Field(ge=0)
    sample_count: int = Field(ge=0)


class WeekdayTrafficWindow(TrafficWindowPoint):
    weekday: int = Field(ge=0, le=6)
    weekday_label: str


class TrafficMethodology(BaseModel):
    sample_interval_minutes: Literal[15] = 15
    bucket_minutes: Literal[120] = 120
    minimum_sessions: int = Field(ge=1)
    session_end_rule: str


class TrafficSummaryResponse(BaseModel):
    gym_id: UUID
    gym_name: str
    gym_slug: str
    district: str
    capacity: int = Field(gt=0)
    timezone: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    cache_hit: bool = False
    data_sufficient: bool
    insufficiency_reason: str | None = None
    contains_demo_data: bool = False
    overlapping_sessions: int = Field(ge=0)
    visits: int = Field(ge=0)
    unique_members: int = Field(ge=0)
    average_visit_minutes: float | None = Field(default=None, ge=0)
    sample_count: int = Field(ge=0)
    average_headcount: float = Field(ge=0)
    average_capacity_percentage: float = Field(ge=0)
    busiest_window: TrafficWindowPoint | None = None
    quietest_window: TrafficWindowPoint | None = None
    buckets: list[TrafficWindowPoint]
    weekday_buckets: list[WeekdayTrafficWindow]
    methodology: TrafficMethodology
