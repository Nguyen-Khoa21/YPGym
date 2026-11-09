from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.operations_schema import PageInfo


class StaffAccountCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    login_name: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$")
    role: Literal["staff", "pt"]
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    gym_id: UUID | None = None

    @field_validator("name", "login_name", "phone", mode="before")
    @classmethod
    def strip_values(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return None if stripped == "" and value is not None else stripped

    @field_validator("login_name")
    @classmethod
    def normalize_login_name(cls, value: str) -> str:
        value = value.lower()
        if ".." in value:
            raise ValueError("Login name cannot contain consecutive periods.")
        return value


class StaffAccountItem(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str | None
    role: str
    must_change_password: bool
    trainer_profile_id: UUID | None
    gym_id: UUID | None = None
    gym_name: str | None = None
    created_at: datetime


class StaffAccountPage(BaseModel):
    items: list[StaffAccountItem]
    page: PageInfo
    internal_email_domain: str


class StaffAccountCreated(BaseModel):
    account: StaffAccountItem
    temporary_password: str
    message: str


class StaffShiftItem(BaseModel):
    id: UUID
    gym_id: UUID
    user_id: UUID
    staff_name: str
    staff_email: str
    role: str
    clocked_in_at: datetime
    clocked_out_at: datetime | None
    duration_minutes: int
    status: Literal["open", "closed"]


class MyStaffShifts(BaseModel):
    open_shift: StaffShiftItem | None
    recent_shifts: list[StaffShiftItem]
    gym_timezone: str


class StaffShiftPage(BaseModel):
    items: list[StaffShiftItem]
    page: PageInfo
    gym_timezone: str


class InPersonMemberRegister(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=32)
    gym_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "phone", mode="before")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class InPersonMemberItem(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str | None
    gym_id: UUID
    gym_name: str


class InPersonMemberRegistered(BaseModel):
    member: InPersonMemberItem
    temporary_password: str
    message: str


class StaffMembershipPaymentRequest(BaseModel):
    """Shared body for QR checkout and cash. The amount and gym are never accepted from the client."""

    plan_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=120)
    gym_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")


class StaffPaymentStatus(BaseModel):
    id: UUID
    status: str
    member_name: str
    plan_name: str | None
    gym_name: str
