from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.operations_schema import PageInfo

Muscle = Literal["chest", "back", "shoulders", "biceps", "triceps", "forearms", "core", "quadriceps", "hamstrings", "glutes", "calves"]
Region = Literal["upper", "lower"]


class ExerciseWrite(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=3000)
    region: Region
    usage_steps: str = Field(min_length=10, max_length=4000)
    safety_note: str = Field(min_length=10, max_length=2000)
    primary_muscles: list[Muscle] = Field(min_length=1, max_length=11)
    secondary_muscles: list[Muscle] = Field(default_factory=list, max_length=11)
    is_illustrative: bool = False
    is_active: bool = True

    @field_validator("name", "description", "usage_steps", "safety_note", mode="before")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("This field cannot be blank.")
        return value.strip()

    @model_validator(mode="after")
    def unique_muscles(self) -> "ExerciseWrite":
        muscles = self.primary_muscles + self.secondary_muscles
        if len(muscles) != len(set(muscles)):
            raise ValueError("A muscle can appear only once per exercise.")
        return self


class ExerciseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    region: Region | None = None
    usage_steps: str | None = None
    safety_note: str | None = None
    primary_muscles: list[Muscle] | None = None
    secondary_muscles: list[Muscle] | None = None
    is_illustrative: bool | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def reject_nulls(self) -> "ExerciseUpdate":
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Exercise fields cannot be null.")
        return self


class ExerciseItem(ExerciseWrite):
    id: UUID
    has_image: bool
    created_at: datetime
    updated_at: datetime


class ExercisePage(BaseModel):
    items: list[ExerciseItem]
    page: PageInfo
