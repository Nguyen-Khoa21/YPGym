from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, JSON, LargeBinary, Numeric, String, Text, UniqueConstraint
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
        CheckConstraint("muscle IN ('chest', 'back', 'front_delts', 'lateral_delts', 'rear_delts', 'rhomboids', 'traps', 'shoulders', 'biceps', 'triceps', 'forearms', 'core', 'quadriceps', 'hamstrings', 'glutes', 'calves')", name="ck_training_exercise_muscles_muscle"),
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


class WorkoutSession(TimestampMixin, Base):
    __tablename__ = "workout_sessions"
    __table_args__ = (UniqueConstraint("user_id", "workout_date", name="uq_workout_sessions_user_date"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_session_id: Mapped[UUID] = mapped_column(ForeignKey("attendance_sessions.id", ondelete="RESTRICT"), nullable=False)
    workout_date: Mapped[date] = mapped_column(Date, nullable=False)


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"
    __table_args__ = (
        UniqueConstraint("session_id", "idempotency_key", name="uq_workout_exercises_session_key"),
        Index("ix_workout_exercises_session_created", "session_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False)
    exercise_id: Mapped[UUID] = mapped_column(ForeignKey("training_exercises.id", ondelete="RESTRICT"), nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(nullable=False)
    name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    primary_muscles_snapshot: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    secondary_muscles_snapshot: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkoutSet(Base):
    __tablename__ = "workout_sets"
    __table_args__ = (
        UniqueConstraint("workout_exercise_id", "set_order", name="uq_workout_sets_exercise_order"),
        CheckConstraint("set_order BETWEEN 1 AND 10", name="ck_workout_sets_order"),
        CheckConstraint("reps > 0", name="ck_workout_sets_reps"),
        CheckConstraint("weight >= 0", name="ck_workout_sets_weight"),
        CheckConstraint("unit IN ('kg', 'lb')", name="ck_workout_sets_unit"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workout_exercise_id: Mapped[UUID] = mapped_column(ForeignKey("workout_exercises.id", ondelete="CASCADE"), nullable=False, index=True)
    set_order: Mapped[int] = mapped_column(nullable=False)
    reps: Mapped[int] = mapped_column(nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(2), nullable=False)
