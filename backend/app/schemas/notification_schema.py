from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.operations_schema import PageInfo


class NotificationPreferenceResponse(BaseModel):
    email_enabled: bool
    in_app_enabled: bool
    expiry_reminders_enabled: bool
    broadcasts_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: bool
    in_app_enabled: bool
    expiry_reminders_enabled: bool
    broadcasts_enabled: bool


class NotificationItem(BaseModel):
    id: UUID
    category: str
    notification_type: str
    title: str
    message: str
    channel: str
    delivery_state: str
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPage(BaseModel):
    items: list[NotificationItem]
    page: PageInfo
    unread_count: int


class BroadcastCreate(BaseModel):
    audience: str = Field(default="all", pattern="^(all|members|normal|advance|vip)$")
    title: str = Field(min_length=3, max_length=180)
    message: str = Field(min_length=5, max_length=3000)
    starts_at: datetime
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "BroadcastCreate":
        if self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("Broadcast end time must be after its start time.")
        return self


class BroadcastUpdate(BaseModel):
    audience: str | None = Field(default=None, pattern="^(all|members|normal|advance|vip)$")
    title: str | None = Field(default=None, min_length=3, max_length=180)
    message: str | None = Field(default=None, min_length=5, max_length=3000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None


class BroadcastItem(BaseModel):
    id: UUID
    audience: str
    title: str
    message: str
    starts_at: datetime
    ends_at: datetime | None
    is_active: bool
    creator_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
