from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class IoTDevice(TimestampMixin, Base):
    __tablename__ = "iot_devices"
    __table_args__ = (
        UniqueConstraint("device_id", name="uq_iot_devices_device_id"),
        Index("ix_iot_devices_device_id", "device_id"),
        Index("ix_iot_devices_is_active", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AttendanceSession(TimestampMixin, Base):
    __tablename__ = "attendance_sessions"
    __table_args__ = (
        Index("ix_attendance_sessions_user_id", "user_id"),
        Index("ix_attendance_sessions_status", "status"),
        Index("ix_attendance_sessions_checked_in_at", "checked_in_at"),
        Index("ix_attendance_sessions_device_id", "device_id"),
        Index(
            "uq_attendance_sessions_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="iot_scanner")
    device_id: Mapped[str | None] = mapped_column(
        ForeignKey("iot_devices.device_id", ondelete="SET NULL"),
    )
    manual_close_reason: Mapped[str | None] = mapped_column(Text)
    closed_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class AttendanceEvent(Base):
    __tablename__ = "attendance_events"
    __table_args__ = (
        Index("ix_attendance_events_session_id", "session_id"),
        Index("ix_attendance_events_user_id", "user_id"),
        Index("ix_attendance_events_event_at", "event_at"),
        Index("ix_attendance_events_event_type", "event_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(100))
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)
