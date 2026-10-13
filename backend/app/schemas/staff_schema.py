from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.operations_schema import PageInfo


class StaffAccountCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    login_name: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$")
    role: Literal["staff", "pt"]
    phone: str | None = Field(default=None, min_length=7, max_length=32)

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
