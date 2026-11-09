from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin

MAIN_GOALS = ("lose_weight", "build_muscle", "stay_fit", "stamina", "not_sure")
TRAINING_WINDOWS = ("early_morning", "daytime", "evening", "night")
DAYS_PER_WEEK = ("1_2", "3_4", "5_plus")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IS NULL OR {column} IN ({', '.join(repr(v) for v in values)})"


class MemberOnboardingProfile(TimestampMixin, Base):
    """Optional training-preference answers; used only for recommendations and aggregate insights."""

    __tablename__ = "member_onboarding_profiles"
    __table_args__ = (
        CheckConstraint(_in("main_goal", MAIN_GOALS), name="ck_member_onboarding_main_goal"),
        CheckConstraint(_in("training_window", TRAINING_WINDOWS), name="ck_member_onboarding_training_window"),
        CheckConstraint(_in("days_per_week", DAYS_PER_WEEK), name="ck_member_onboarding_days_per_week"),
        Index("ix_member_onboarding_profiles_closer_gym", "closer_gym_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    is_new_to_gym: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    prefers_uncrowded_hours: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    closer_gym_id: Mapped[UUID | None] = mapped_column(ForeignKey("gym_locations.id", ondelete="SET NULL"), nullable=True)
    main_goal: Mapped[str | None] = mapped_column(String(16), nullable=True)
    training_window: Mapped[str | None] = mapped_column(String(16), nullable=True)
    days_per_week: Mapped[str | None] = mapped_column(String(8), nullable=True)
    interested_in_classes: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    interested_in_personal_trainer: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
