from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.operations_schema import PageInfo


class QrTokenResponse(BaseModel):
    token: str
    issued_at: datetime
    expires_at: datetime
    ttl_seconds: int
    membership_status: str


class ScannerRequest(BaseModel):
    device_id: str = Field(min_length=3, max_length=100)
    qr_token: str = Field(min_length=20)


class ScannerResponse(BaseModel):
    code: str
    message: str
    session_id: UUID
    member_id: UUID
    occurred_at: datetime
    occupancy: "CrowdednessResponse"


class CrowdednessResponse(BaseModel):
    active_count: int
    capacity: int
    percentage: float
    status: str
    calculated_at: datetime


class AttendanceEventItem(BaseModel):
    id: UUID
    event_type: str
    event_at: datetime
    source: str
    device_id: str | None


class AttendanceSessionItem(BaseModel):
    id: UUID
    user_id: UUID
    member_name: str | None = None
    member_email: str | None = None
    checked_in_at: datetime
    closed_at: datetime | None
    status: str
    source: str
    device_id: str | None
    manual_close_reason: str | None
    events: list[AttendanceEventItem] = Field(default_factory=list)


class AttendancePage(BaseModel):
    items: list[AttendanceSessionItem]
    page: PageInfo
    distinct_visit_days: list[date] = Field(default_factory=list)
    gym_timezone: str | None = None


class ManualCloseRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)


class PeakHourCell(BaseModel):
    weekday: int
    weekday_label: str
    hour: int
    visits: int


class PeakHoursResponse(BaseModel):
    cells: list[PeakHourCell]
    occupancy: CrowdednessResponse
    visits_today: int
    busiest_hour: str | None
    date_from: datetime
    date_to: datetime
