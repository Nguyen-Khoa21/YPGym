from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TrainingExercise(TimestampMixin, Base):
    __tablename__ = "training_exercises"
    __table_args__ = (
        CheckConstraint("region IN ('upper', 'lower')", name="ck_training_exercises_region"),
        Index("ix_training_exercises_region_active", "region", "is_active"),
        Index("ix_training_exercises_name", "name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str] = mapped_column(String(8), nullable=False)
    usage_steps: Mapped[str] = mapped_column(Text, nullable=False)
    safety_note: Mapped[str] = mapped_column(Text, nullable=False)
    is_illustrative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class TrainingExerciseMuscle(Base):
    __tablename__ = "training_exercise_muscles"
    __table_args__ = (
        UniqueConstraint("exercise_id", "muscle", name="uq_training_exercise_muscles_exercise_muscle"),
        CheckConstraint("role IN ('primary', 'secondary')", name="ck_training_exercise_muscles_role"),
        CheckConstraint("muscle IN ('chest', 'back', 'shoulders', 'biceps', 'triceps', 'forearms', 'core', 'quadriceps', 'hamstrings', 'glutes', 'calves')", name="ck_training_exercise_muscles_muscle"),
        Index("ix_training_exercise_muscles_muscle", "muscle"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    exercise_id: Mapped[UUID] = mapped_column(ForeignKey("training_exercises.id", ondelete="CASCADE"), nullable=False)
    muscle: Mapped[str] = mapped_column(String(24), nullable=False)
    role: Mapped[str] = mapped_column(String(9), nullable=False)


class TrainingExerciseImage(Base):
    __tablename__ = "training_exercise_images"

    exercise_id: Mapped[UUID] = mapped_column(ForeignKey("training_exercises.id", ondelete="CASCADE"), primary_key=True)
    image_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
