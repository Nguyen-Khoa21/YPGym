"""Expand YPTrain muscle taxonomy.

Revision ID: 20260924_0012
Revises: 20260922_0011
"""

from alembic import op


revision = "20260924_0012"
down_revision = "20260922_0011"
branch_labels = None
depends_on = None


MUSCLES = "'chest', 'back', 'front_delts', 'lateral_delts', 'rear_delts', 'rhomboids', 'traps', 'shoulders', 'biceps', 'triceps', 'forearms', 'core', 'quadriceps', 'hamstrings', 'glutes', 'calves'"
LEGACY_MUSCLES = "'chest', 'back', 'shoulders', 'biceps', 'triceps', 'forearms', 'core', 'quadriceps', 'hamstrings', 'glutes', 'calves'"


def upgrade() -> None:
    op.drop_constraint("ck_training_exercise_muscles_muscle", "training_exercise_muscles", type_="check")
    op.create_check_constraint(
        "ck_training_exercise_muscles_muscle",
        "training_exercise_muscles",
        f"muscle IN ({MUSCLES})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_training_exercise_muscles_muscle", "training_exercise_muscles", type_="check")
    op.create_check_constraint(
        "ck_training_exercise_muscles_muscle",
        "training_exercise_muscles",
        f"muscle IN ({LEGACY_MUSCLES})",
    )
