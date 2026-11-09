from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MainGoal = Literal["lose_weight", "build_muscle", "stay_fit", "stamina", "not_sure"]
TrainingWindow = Literal["early_morning", "daytime", "evening", "night"]
DaysPerWeek = Literal["1_2", "3_4", "5_plus"]
OnboardingStatus = Literal["not_started", "skipped", "partial", "complete"]


class OnboardingAnswers(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_new_to_gym: bool | None = None
    prefers_uncrowded_hours: bool | None = None
    closer_gym_id: UUID | None = None
    main_goal: MainGoal | None = None
    training_window: TrainingWindow | None = None
    days_per_week: DaysPerWeek | None = None
    interested_in_classes: bool | None = None
    interested_in_personal_trainer: bool | None = None


class OnboardingResponse(OnboardingAnswers):
    status: OnboardingStatus
    completed_at: datetime | None = None
    dismissed_at: datetime | None = None


class RecommendedGym(BaseModel):
    id: UUID
    name: str
    slug: str
    district: str


class QuietHours(BaseModel):
    gym_id: UUID
    gym_name: str
    label: str
    start_hour: int = Field(ge=0, le=22)
    end_hour: int = Field(ge=2, le=24)
    average_capacity_percentage: float = Field(ge=0)


class RecommendationsResponse(BaseModel):
    recommended_gym: RecommendedGym | None = None
    quiet_hours: QuietHours | None = None
    quiet_hours_reason: Literal["not_enough_data"] | None = None


class InsightBucket(BaseModel):
    key: str
    label: str
    count: int | None = None
    percent: float | None = None
    suppressed: bool = False


class InsightMetric(BaseModel):
    key: str
    label: str
    answered: int | None = None
    suppressed: bool = False
    buckets: list[InsightBucket] = Field(default_factory=list)


class GymSplitRow(BaseModel):
    gym_id: UUID
    gym_name: str
    closer_count: int | None = None
    closer_suppressed: bool = False
    home_members: int | None = None
    home_suppressed: bool = False


class OnboardingInsightsResponse(BaseModel):
    gym_id: UUID | None = None
    min_group_size: int
    members: int
    respondents: int | None = None
    respondents_suppressed: bool = False
    response_rate_percent: float | None = None
    metrics: list[InsightMetric]
    gym_split: list[GymSplitRow] = Field(default_factory=list)
    generated_at: datetime
