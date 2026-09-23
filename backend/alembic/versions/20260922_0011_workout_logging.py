"""add attendance-linked daily workout logging

Revision ID: 20260922_0011
Revises: 20260922_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260922_0011"
down_revision: str | Sequence[str] | None = "20260922_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attendance_session_id", sa.Uuid(), sa.ForeignKey("attendance_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("workout_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "workout_date", name="uq_workout_sessions_user_date"),
    )
    op.create_index("ix_workout_sessions_user_id", "workout_sessions", ["user_id"])
    op.create_table(
        "workout_exercises",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), sa.ForeignKey("training_exercises.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("name_snapshot", sa.String(160), nullable=False),
        sa.Column("primary_muscles_snapshot", sa.JSON(), nullable=False),
        sa.Column("secondary_muscles_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "idempotency_key", name="uq_workout_exercises_session_key"),
    )
    op.create_index("ix_workout_exercises_session_created", "workout_exercises", ["session_id", "created_at"])
    op.create_table(
        "workout_sets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workout_exercise_id", sa.Uuid(), sa.ForeignKey("workout_exercises.id", ondelete="CASCADE"), nullable=False),
        sa.Column("set_order", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Numeric(6, 2), nullable=False),
        sa.Column("unit", sa.String(2), nullable=False),
        sa.UniqueConstraint("workout_exercise_id", "set_order", name="uq_workout_sets_exercise_order"),
        sa.CheckConstraint("set_order BETWEEN 1 AND 10", name="ck_workout_sets_order"),
        sa.CheckConstraint("reps > 0", name="ck_workout_sets_reps"),
        sa.CheckConstraint("weight >= 0", name="ck_workout_sets_weight"),
        sa.CheckConstraint("unit IN ('kg', 'lb')", name="ck_workout_sets_unit"),
    )
    op.create_index("ix_workout_sets_workout_exercise_id", "workout_sets", ["workout_exercise_id"])


def downgrade() -> None:
    op.drop_index("ix_workout_sets_workout_exercise_id", table_name="workout_sets")
    op.drop_table("workout_sets")
    op.drop_index("ix_workout_exercises_session_created", table_name="workout_exercises")
    op.drop_table("workout_exercises")
    op.drop_index("ix_workout_sessions_user_id", table_name="workout_sessions")
    op.drop_table("workout_sessions")
