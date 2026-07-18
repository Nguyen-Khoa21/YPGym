from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.operations_schema import PageInfo


class TrainerItem(BaseModel):
    id: UUID
    display_name: str
    specialty: str | None
    is_active: bool


class ClassCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    class_type: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=3000)
    start_at: datetime
    end_at: datetime
    capacity: int = Field(ge=1, le=500)
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
