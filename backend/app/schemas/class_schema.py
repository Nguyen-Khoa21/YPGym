from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.operations_schema import PageInfo


class TrainerClassSummary(BaseModel):
    id: UUID
    title: str
    class_type: str
    start_at: datetime
    end_at: datetime
    location: str


class TrainerItem(BaseModel):
    id: UUID
    display_name: str
    bio: str | None
    specialty: str | None
    availability_summary: str | None
    is_active: bool
    upcoming_classes: list[TrainerClassSummary] = Field(default_factory=list)


class TrainerCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=160)
    bio: str | None = Field(default=None, max_length=3000)
    specialty: str | None = Field(default=None, max_length=180)
    availability_summary: str | None = Field(default=None, max_length=500)
    user_id: UUID | None = None


class TrainerUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    bio: str | None = Field(default=None, max_length=3000)
    specialty: str | None = Field(default=None, max_length=180)
    availability_summary: str | None = Field(default=None, max_length=500)
    user_id: UUID | None = None


class TrainerAdminItem(TrainerItem):
    user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ClassCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    class_type: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=3000)
    start_at: datetime
    end_at: datetime
    capacity: int = Field(ge=1, le=500)
    price_vnd: int = Field(ge=1, le=1_000_000_000)
    trainer_id: UUID | None = None
    location: str = Field(min_length=2, max_length=160)

    @model_validator(mode="after")
    def validate_times(self) -> "ClassCreate":
        if self.end_at <= self.start_at:
            raise ValueError("Class end time must be after its start time.")
        return self


class ClassUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    class_type: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=3000)
    start_at: datetime | None = None
    end_at: datetime | None = None
    capacity: int | None = Field(default=None, ge=1, le=500)
    price_vnd: int | None = Field(default=None, ge=1, le=1_000_000_000)
    trainer_id: UUID | None = None
    location: str | None = Field(default=None, min_length=2, max_length=160)


class ClassCancel(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)


class ClassItem(BaseModel):
    id: UUID
    title: str
    class_type: str
    description: str | None
    start_at: datetime
    end_at: datetime
    capacity: int
    price_vnd: int | None
    status: str
    trainer_id: UUID | None
    trainer_name: str | None
    location: str
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime


class ClassPage(BaseModel):
    items: list[ClassItem]
    page: PageInfo
    scheduled_count: int
    cancelled_count: int


class MemberClassItem(BaseModel):
    id: UUID
    title: str
    class_type: str
    description: str | None
    start_at: datetime
    end_at: datetime
    capacity: int
    price_vnd: int | None
    status: str
    location: str
    confirmed_booking_count: int
    remaining_capacity: int
    trainer: TrainerItem | None
    member_booking_id: UUID | None
    member_booking_status: str | None
    member_waitlist_status: str | None
    waitlist_position: int | None
    member_state: str


class MemberClassList(BaseModel):
    items: list[MemberClassItem]
    booking_eligible: bool
    eligibility_status: str
    eligibility_reason: str | None


class BookingItem(BaseModel):
    id: UUID
    status: str
    price_vnd: int | None
    entitlement_source: str
    reserved_until: datetime | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    refund_status: str
    payment_id: UUID | None
    payment_status: str | None
    invoice_id: UUID | None
    invoice_download_url: str | None
    attended_at: datetime | None
    created_at: datetime
    updated_at: datetime
    cancellation_cutoff: datetime
    can_cancel: bool
    gym_class: MemberClassItem


class WaitlistItem(BaseModel):
    id: UUID
    status: str
    position: int
    created_at: datetime
    updated_at: datetime
    gym_class: MemberClassItem


class MemberBookings(BaseModel):
    bookings: list[BookingItem]
    waitlists: list[WaitlistItem]
    cancellation_window_hours: int
    cancellation_terms: str


class ClassCheckoutRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    locale: Literal["vn", "en"] = "vn"
    bank_code: Literal["VNPAYQR", "VNBANK", "INTCARD"] | None = None
    client_platform: Literal["web", "mobile", "mobile_web"] = "web"

    model_config = ConfigDict(extra="forbid")


class ClassCheckoutResponse(BaseModel):
    booking_id: UUID
    transaction_id: UUID
    txn_ref: str
    payment_url: str
    expires_at: datetime


class BookingCancel(BaseModel):
    reason: str = Field(default="Cancelled by member", min_length=3, max_length=500)


class BookingRefundResolution(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
