"""core auth and membership tables

Revision ID: 20260702_0002
Revises: 20260610_0001
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260702_0002"
down_revision: str | Sequence[str] | None = "20260610_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


USER_ROLES = ("member", "staff", "manager", "admin", "pt")
MEMBER_TIERS = ("normal", "advance", "vip")
MEMBERSHIP_STATUSES = (
    "pending_verification",
    "active",
    "expiring_soon",
    "expired",
    "frozen",
    "cancelled",
    "revoked",
)
CONFIG_VALUE_TYPES = ("string", "integer", "decimal", "boolean")


def csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pending_email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"role IN ({csv(USER_ROLES)})", name="ck_users_role"),
        sa.CheckConstraint(f"tier IN ({csv(MEMBER_TIERS)})", name="ck_users_tier"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_phone", "users", ["phone"], unique=False)

    op.create_table(
        "email_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_verifications_user_id", "email_verifications", ["user_id"], unique=False)
    op.create_index("ix_email_verifications_token_hash", "email_verifications", ["token_hash"], unique=True)

    op.create_table(
        "password_resets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"], unique=False)
    op.create_index("ix_password_resets_token_hash", "password_resets", ["token_hash"], unique=True)

    op.create_table(
        "membership_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("duration_months", sa.Integer(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("discount_percent", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("tier_availability", sa.String(length=32), nullable=True),
        sa.Column("benefits", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            f"tier_availability IS NULL OR tier_availability IN ({csv(MEMBER_TIERS)})",
            name="ck_membership_plans_tier_availability",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_membership_plans_name"),
    )
    op.create_index("ix_membership_plans_duration_months", "membership_plans", ["duration_months"], unique=False)
    op.create_index("ix_membership_plans_is_active", "membership_plans", ["is_active"], unique=False)

    op.create_table(
        "user_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"status IN ({csv(MEMBERSHIP_STATUSES)})", name="ck_user_memberships_status"),
        sa.ForeignKeyConstraint(["plan_id"], ["membership_plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_memberships_user_id", "user_memberships", ["user_id"], unique=False)
    op.create_index("ix_user_memberships_status", "user_memberships", ["status"], unique=False)
    op.create_index("ix_user_memberships_expiry_date", "user_memberships", ["expiry_date"], unique=False)

    op.create_table(
        "system_configurations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"value_type IN ({csv(CONFIG_VALUE_TYPES)})", name="ck_system_configurations_value_type"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_system_configurations_key"),
    )
    op.create_index("ix_system_configurations_key", "system_configurations", ["key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_system_configurations_key", table_name="system_configurations")
    op.drop_table("system_configurations")

    op.drop_index("ix_user_memberships_expiry_date", table_name="user_memberships")
    op.drop_index("ix_user_memberships_status", table_name="user_memberships")
    op.drop_index("ix_user_memberships_user_id", table_name="user_memberships")
    op.drop_table("user_memberships")

    op.drop_index("ix_membership_plans_is_active", table_name="membership_plans")
    op.drop_index("ix_membership_plans_duration_months", table_name="membership_plans")
    op.drop_table("membership_plans")

    op.drop_index("ix_password_resets_token_hash", table_name="password_resets")
    op.drop_index("ix_password_resets_user_id", table_name="password_resets")
    op.drop_table("password_resets")

    op.drop_index("ix_email_verifications_token_hash", table_name="email_verifications")
    op.drop_index("ix_email_verifications_user_id", table_name="email_verifications")
    op.drop_table("email_verifications")

    op.drop_index("ix_users_phone", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
