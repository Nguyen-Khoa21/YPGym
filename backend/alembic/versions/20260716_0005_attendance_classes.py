"""attendance, IoT devices, trainers and class scheduling

Revision ID: 20260716_0005
Revises: 20260716_0004
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0005"
down_revision: str | Sequence[str] | None = "20260716_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "iot_devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("api_key_hash", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", name="uq_iot_devices_device_id"),
    )
    op.create_index("ix_iot_devices_device_id", "iot_devices", ["device_id"])
    op.create_index("ix_iot_devices_is_active", "iot_devices", ["is_active"])

    op.create_table(
        "attendance_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("device_id", sa.String(length=100), nullable=True),
        sa.Column("manual_close_reason", sa.Text(), nullable=True),
        sa.Column("closed_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'checked_out', 'timed_out', 'manual_closed')",
            name="ck_attendance_sessions_status",
        ),
        sa.ForeignKeyConstraint(["closed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["device_id"], ["iot_devices.device_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attendance_sessions_user_id", "attendance_sessions", ["user_id"])
    op.create_index("ix_attendance_sessions_status", "attendance_sessions", ["status"])
    op.create_index("ix_attendance_sessions_checked_in_at", "attendance_sessions", ["checked_in_at"])
    op.create_index("ix_attendance_sessions_device_id", "attendance_sessions", ["device_id"])
    op.create_index(
        "uq_attendance_sessions_active_user",
        "attendance_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "attendance_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("device_id", sa.String(length=100), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "event_type IN ('check_in', 'check_out', 'timeout', 'manual_close')",
            name="ck_attendance_events_event_type",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["attendance_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attendance_events_session_id", "attendance_events", ["session_id"])
    op.create_index("ix_attendance_events_user_id", "attendance_events", ["user_id"])
    op.create_index("ix_attendance_events_event_at", "attendance_events", ["event_at"])
    op.create_index("ix_attendance_events_event_type", "attendance_events", ["event_type"])

    op.create_table(
        "personal_trainers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("specialty", sa.String(length=180), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_personal_trainers_user_id"),
    )
    op.create_index("ix_personal_trainers_is_active", "personal_trainers", ["is_active"])

    op.create_table(
        "classes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("class_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="scheduled", nullable=False),
        sa.Column("trainer_id", sa.Uuid(), nullable=True),
        sa.Column("location", sa.String(length=160), nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("cancelled_by_id", sa.Uuid(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("capacity > 0", name="ck_classes_capacity_positive"),
        sa.CheckConstraint("end_at > start_at", name="ck_classes_time_order"),
        sa.CheckConstraint("status IN ('scheduled', 'cancelled', 'completed')", name="ck_classes_status"),
        sa.ForeignKeyConstraint(["cancelled_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["trainer_id"], ["personal_trainers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_classes_start_at", "classes", ["start_at"])
    op.create_index("ix_classes_status", "classes", ["status"])
    op.create_index("ix_classes_trainer_id", "classes", ["trainer_id"])
    op.create_index("ix_classes_type_start", "classes", ["class_type", "start_at"])

    op.create_table(
        "class_bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="booked", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('booked', 'cancelled')", name="ck_class_bookings_status"),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_id", "user_id", name="uq_class_bookings_class_user"),
    )
    op.create_index("ix_class_bookings_user_id", "class_bookings", ["user_id"])
    op.create_index("ix_class_bookings_class_status", "class_bookings", ["class_id", "status"])

    op.create_table(
        "class_waitlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="waiting", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("position > 0", name="ck_class_waitlists_position_positive"),
        sa.CheckConstraint("status IN ('waiting', 'promoted', 'cancelled')", name="ck_class_waitlists_status"),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_id", "position", name="uq_class_waitlists_class_position"),
        sa.UniqueConstraint("class_id", "user_id", name="uq_class_waitlists_class_user"),
    )
    op.create_index(
        "ix_class_waitlists_class_status_position",
        "class_waitlists",
        ["class_id", "status", "position"],
    )
    op.create_index("ix_class_waitlists_user_id", "class_waitlists", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_class_waitlists_user_id", table_name="class_waitlists")
    op.drop_index("ix_class_waitlists_class_status_position", table_name="class_waitlists")
    op.drop_table("class_waitlists")
    op.drop_index("ix_class_bookings_class_status", table_name="class_bookings")
    op.drop_index("ix_class_bookings_user_id", table_name="class_bookings")
    op.drop_table("class_bookings")
    op.drop_index("ix_classes_type_start", table_name="classes")
    op.drop_index("ix_classes_trainer_id", table_name="classes")
    op.drop_index("ix_classes_status", table_name="classes")
    op.drop_index("ix_classes_start_at", table_name="classes")
    op.drop_table("classes")
    op.drop_index("ix_personal_trainers_is_active", table_name="personal_trainers")
    op.drop_table("personal_trainers")
    op.drop_index("ix_attendance_events_event_type", table_name="attendance_events")
    op.drop_index("ix_attendance_events_event_at", table_name="attendance_events")
    op.drop_index("ix_attendance_events_user_id", table_name="attendance_events")
    op.drop_index("ix_attendance_events_session_id", table_name="attendance_events")
    op.drop_table("attendance_events")
    op.drop_index("uq_attendance_sessions_active_user", table_name="attendance_sessions")
    op.drop_index("ix_attendance_sessions_device_id", table_name="attendance_sessions")
    op.drop_index("ix_attendance_sessions_checked_in_at", table_name="attendance_sessions")
    op.drop_index("ix_attendance_sessions_status", table_name="attendance_sessions")
    op.drop_index("ix_attendance_sessions_user_id", table_name="attendance_sessions")
    op.drop_table("attendance_sessions")
    op.drop_index("ix_iot_devices_is_active", table_name="iot_devices")
    op.drop_index("ix_iot_devices_device_id", table_name="iot_devices")
    op.drop_table("iot_devices")
