"""membership lifecycle, CRM operations, notifications and audit

Revision ID: 20260716_0004
Revises: 20260702_0003
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0004"
down_revision: str | Sequence[str] | None = "20260702_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_memberships", sa.Column("frozen_from", sa.Date(), nullable=True))
    op.add_column("user_memberships", sa.Column("frozen_until", sa.Date(), nullable=True))
    op.add_column("user_memberships", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_memberships", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_memberships", sa.Column("revoked_by_id", sa.Uuid(), nullable=True))
    op.add_column("user_memberships", sa.Column("revoked_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_user_memberships_revoked_by_id_users",
        "user_memberships",
        "users",
        ["revoked_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "membership_freeze_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("requested_start_date", sa.Date(), nullable=False),
        sa.Column("requested_end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_membership_freeze_requests_status"),
        sa.ForeignKeyConstraint(["membership_id"], ["user_memberships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_membership_freeze_requests_user_id", "membership_freeze_requests", ["user_id"])
    op.create_index("ix_membership_freeze_requests_status", "membership_freeze_requests", ["status"])
    op.create_index(
        "uq_membership_freeze_requests_open_membership",
        "membership_freeze_requests",
        ["membership_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        "membership_cancellation_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_membership_cancellation_requests_status"),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('refund', 'account_credit', 'forfeit')",
            name="ck_membership_cancellation_requests_outcome",
        ),
        sa.ForeignKeyConstraint(["membership_id"], ["user_memberships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_membership_cancellation_requests_user_id", "membership_cancellation_requests", ["user_id"])
    op.create_index("ix_membership_cancellation_requests_status", "membership_cancellation_requests", ["status"])
    op.create_index(
        "uq_membership_cancellation_requests_open_membership",
        "membership_cancellation_requests",
        ["membership_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(length=80), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("before_data", sa.JSON(), nullable=True),
        sa.Column("after_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_target_user_id", "audit_logs", ["target_user_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("expiry_reminders_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("broadcasts_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("notification_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(length=24), nullable=False),
        sa.Column("delivery_state", sa.String(length=24), nullable=False),
        sa.Column("dedupe_key", sa.String(length=220), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("channel IN ('in_app', 'email')", name="ck_notifications_channel"),
        sa.CheckConstraint("delivery_state IN ('pending', 'delivered', 'skipped')", name="ck_notifications_delivery_state"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_notifications_dedupe_key"),
    )
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read_at"])

    op.create_table(
        "broadcast_announcements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audience", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("creator_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="ck_broadcast_announcements_time_order"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_broadcast_announcements_active_period",
        "broadcast_announcements",
        ["is_active", "starts_at", "ends_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_broadcast_announcements_active_period", table_name="broadcast_announcements")
    op.drop_table("broadcast_announcements")
    op.drop_index("ix_notifications_user_read", table_name="notifications")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("notification_preferences")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_target_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("uq_membership_cancellation_requests_open_membership", table_name="membership_cancellation_requests")
    op.drop_index("ix_membership_cancellation_requests_status", table_name="membership_cancellation_requests")
    op.drop_index("ix_membership_cancellation_requests_user_id", table_name="membership_cancellation_requests")
    op.drop_table("membership_cancellation_requests")
    op.drop_index("uq_membership_freeze_requests_open_membership", table_name="membership_freeze_requests")
    op.drop_index("ix_membership_freeze_requests_status", table_name="membership_freeze_requests")
    op.drop_index("ix_membership_freeze_requests_user_id", table_name="membership_freeze_requests")
    op.drop_table("membership_freeze_requests")
    op.drop_constraint("fk_user_memberships_revoked_by_id_users", "user_memberships", type_="foreignkey")
    op.drop_column("user_memberships", "revoked_reason")
    op.drop_column("user_memberships", "revoked_by_id")
    op.drop_column("user_memberships", "revoked_at")
    op.drop_column("user_memberships", "cancelled_at")
    op.drop_column("user_memberships", "frozen_until")
    op.drop_column("user_memberships", "frozen_from")
