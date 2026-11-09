from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MemberTier, UserRole
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("phone", name="uq_users_phone"),
        CheckConstraint("registration_channel IN ('online', 'in_person')", name="ck_users_registration_channel"),
        Index("ix_users_email", "email"),
        Index("ix_users_phone", "phone"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(32),
        default=UserRole.MEMBER.value,
        nullable=False,
    )
    tier: Mapped[str] = mapped_column(
        String(32),
        default=MemberTier.NORMAL.value,
        nullable=False,
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    registration_channel: Mapped[str] = mapped_column(
        String(16),
        default="online",
        server_default="online",
        nullable=False,
    )
    registered_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name="fk_users_registered_by_user_id_users"),
        nullable=True,
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    pending_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    email_verifications = relationship(
        "EmailVerification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_resets = relationship(
        "PasswordReset",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    memberships = relationship(
        "UserMembership",
        back_populates="user",
        foreign_keys="UserMembership.user_id",
    )
    payments = relationship("Payment", back_populates="user")
    invoices = relationship("Invoice", back_populates="user")
