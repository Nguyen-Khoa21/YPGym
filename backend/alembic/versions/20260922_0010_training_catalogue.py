"""add shared training catalogue

Revision ID: 20260922_0010
Revises: 20260922_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260922_0010"
down_revision: str | Sequence[str] | None = "20260922_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "training_exercises",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("region", sa.String(8), nullable=False),
        sa.Column("usage_steps", sa.Text(), nullable=False),
        sa.Column("safety_note", sa.Text(), nullable=False),
        sa.Column("is_illustrative", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("region IN ('upper', 'lower')", name="ck_training_exercises_region"),
    )
    op.create_index("ix_training_exercises_region_active", "training_exercises", ["region", "is_active"])
    op.create_index("ix_training_exercises_name", "training_exercises", ["name"])
    op.create_table(
        "training_exercise_muscles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("exercise_id", sa.Uuid(), sa.ForeignKey("training_exercises.id", ondelete="CASCADE"), nullable=False),
        sa.Column("muscle", sa.String(24), nullable=False),
        sa.Column("role", sa.String(9), nullable=False),
        sa.UniqueConstraint("exercise_id", "muscle", name="uq_training_exercise_muscles_exercise_muscle"),
        sa.CheckConstraint("role IN ('primary', 'secondary')", name="ck_training_exercise_muscles_role"),
        sa.CheckConstraint("muscle IN ('chest', 'back', 'shoulders', 'biceps', 'triceps', 'forearms', 'core', 'quadriceps', 'hamstrings', 'glutes', 'calves')", name="ck_training_exercise_muscles_muscle"),
    )
    op.create_index("ix_training_exercise_muscles_muscle", "training_exercise_muscles", ["muscle"])
    op.create_table(
        "training_exercise_images",
        sa.Column("exercise_id", sa.Uuid(), sa.ForeignKey("training_exercises.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("training_exercise_images")
    op.drop_index("ix_training_exercise_muscles_muscle", table_name="training_exercise_muscles")
    op.drop_table("training_exercise_muscles")
    op.drop_index("ix_training_exercises_name", table_name="training_exercises")
    op.drop_index("ix_training_exercises_region_active", table_name="training_exercises")
    op.drop_table("training_exercises")
