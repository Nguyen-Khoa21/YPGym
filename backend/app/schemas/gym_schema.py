from datetime import datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GymLocationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    district: str
    address: str
    timezone: str
    capacity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class GymLocationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    district: str = Field(min_length=2, max_length=100)
    address: str = Field(min_length=2, max_length=255)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", min_length=3, max_length=64)
    capacity: int = Field(ge=1, le=5000)
    is_active: bool = True

    @field_validator("name", "slug", "district", "address", "timezone", mode="before")
    @classmethod
    def strip_values(cls, value: str) -> str:
        return value.strip()

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Timezone must be a valid IANA timezone.") from exc
        return value


class GymLocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    slug: str | None = Field(default=None, min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    district: str | None = Field(default=None, min_length=2, max_length=100)
    address: str | None = Field(default=None, min_length=2, max_length=255)
    timezone: str | None = Field(default=None, min_length=3, max_length=64)
    capacity: int | None = Field(default=None, ge=1, le=5000)
    is_active: bool | None = None

    @field_validator("name", "slug", "district", "address", "timezone", mode="before")
    @classmethod
    def strip_values(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Timezone must be a valid IANA timezone.") from exc
        return value


class WorkforceAssignmentCreate(BaseModel):
    user_id: UUID
    gym_id: UUID


class WorkforceAssignmentItem(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    gym_id: UUID
    gym_name: str
    assigned_role: Literal["manager", "staff", "pt"]
    is_active: bool
    created_at: datetime
