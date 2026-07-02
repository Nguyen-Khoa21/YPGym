from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MemberTier, MembershipStatus
from app.models.mixins import TimestampMixin


class MembershipPlan(TimestampMixin, Base):
    __tablename__ = "membership_plans"
    __table_args__ = (
        Index("ix_membership_plans_duration_months", "duration_months"),
        Index("ix_membership_plans_is_active", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        server_default="0",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    tier_availability: Mapped[str | None] = mapped_column(
        String(32),
        default=MemberTier.NORMAL.value,
        nullable=True,
    )
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    memberships = relationship("UserMembership", back_populates="plan")
    payments = relationship("Payment", back_populates="plan")


class UserMembership(TimestampMixin, Base):
    __tablename__ = "user_memberships"
    __table_args__ = (
        Index("ix_user_memberships_user_id", "user_id"),
        Index("ix_user_memberships_status", "status"),
        Index("ix_user_memberships_expiry_date", "expiry_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("membership_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=MembershipStatus.ACTIVE.value,
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)

    user = relationship("User", back_populates="memberships")
    plan = relationship("MembershipPlan", back_populates="memberships")
    payments = relationship("Payment", back_populates="membership")
