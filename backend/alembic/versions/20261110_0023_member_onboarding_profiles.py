"""Add member onboarding profiles.

Revision ID: 20261110_0023
Revises: 20261110_0022
"""

from alembic import op
import sqlalchemy as sa


revision = "20261110_0023"
down_revision = "20261110_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "member_onboarding_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("is_new_to_gym", sa.Boolean(), nullable=True),
        sa.Column("prefers_uncrowded_hours", sa.Boolean(), nullable=True),
        sa.Column("closer_gym_id", sa.Uuid(), nullable=True),
        sa.Column("main_goal", sa.String(length=16), nullable=True),
        sa.Column("training_window", sa.String(length=16), nullable=True),
        sa.Column("days_per_week", sa.String(length=8), nullable=True),
        sa.Column("interested_in_classes", sa.Boolean(), nullable=True),
        sa.Column("interested_in_personal_trainer", sa.Boolean(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "main_goal IS NULL OR main_goal IN ('lose_weight', 'build_muscle', 'stay_fit', 'stamina', 'not_sure')",
            name="ck_member_onboarding_main_goal",
        ),
        sa.CheckConstraint(
            "training_window IS NULL OR training_window IN ('early_morning', 'daytime', 'evening', 'night')",
            name="ck_member_onboarding_training_window",
        ),
        sa.CheckConstraint(
            "days_per_week IS NULL OR days_per_week IN ('1_2', '3_4', '5_plus')",
            name="ck_member_onboarding_days_per_week",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["closer_gym_id"], ["gym_locations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_member_onboarding_profiles_closer_gym", "member_onboarding_profiles", ["closer_gym_id"])


def downgrade() -> None:
    op.drop_index("ix_member_onboarding_profiles_closer_gym", table_name="member_onboarding_profiles")
    op.drop_table("member_onboarding_profiles")
