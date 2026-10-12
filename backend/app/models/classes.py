from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PersonalTrainer(TimestampMixin, Base):
    __tablename__ = "personal_trainers"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_personal_trainers_user_id"),
        Index("ix_personal_trainers_is_active", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    specialty: Mapped[str | None] = mapped_column(String(180))
    availability_summary: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class GymClass(TimestampMixin, Base):
    __tablename__ = "classes"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_classes_capacity_positive"),
        CheckConstraint("price_vnd IS NULL OR price_vnd > 0", name="ck_classes_price_vnd_positive"),
        CheckConstraint("end_at > start_at", name="ck_classes_time_order"),
        Index("ix_classes_start_at", "start_at"),
        Index("ix_classes_status", "status"),
        Index("ix_classes_trainer_id", "trainer_id"),
        Index("ix_classes_type_start", "class_type", "start_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    class_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_vnd: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    trainer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("personal_trainers.id", ondelete="SET NULL"),
    )
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClassBooking(TimestampMixin, Base):
    __tablename__ = "class_bookings"
    __table_args__ = (
        UniqueConstraint("class_id", "user_id", name="uq_class_bookings_class_user"),
        CheckConstraint("price_vnd IS NULL OR price_vnd > 0", name="ck_class_bookings_price_vnd_positive"),
        CheckConstraint(
            "status IN ('pending_payment', 'confirmed', 'cancelled', 'expired', 'payment_failed', 'refunded')",
            name="ck_class_bookings_status",
        ),
        CheckConstraint("entitlement_source IN ('legacy', 'paid')", name="ck_class_bookings_entitlement_source"),
        CheckConstraint("refund_status IN ('none', 'required', 'resolved')", name="ck_class_bookings_refund_status"),
        Index("ix_class_bookings_user_id", "user_id"),
        Index("ix_class_bookings_class_status", "class_id", "status"),
        Index(
            "uq_class_bookings_current_payment_id",
            "current_payment_id",
            unique=True,
            postgresql_where=text("current_payment_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending_payment")
    price_vnd: Mapped[int | None] = mapped_column(BigInteger)
    entitlement_source: Mapped[str] = mapped_column(String(16), nullable=False, default="paid")
    current_payment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "payments.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_class_bookings_current_payment_id_payments",
        ),
    )
    reserved_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    refund_status: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    attended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_in_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    gym_class = relationship("GymClass", foreign_keys=[class_id])
    current_payment = relationship("Payment", foreign_keys=[current_payment_id], post_update=True)


class ClassWaitlist(TimestampMixin, Base):
    __tablename__ = "class_waitlists"
    __table_args__ = (
        CheckConstraint("position > 0", name="ck_class_waitlists_position_positive"),
        UniqueConstraint("class_id", "user_id", name="uq_class_waitlists_class_user"),
        UniqueConstraint("class_id", "position", name="uq_class_waitlists_class_position"),
        Index("ix_class_waitlists_class_status_position", "class_id", "status", "position"),
        Index("ix_class_waitlists_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="waiting")
