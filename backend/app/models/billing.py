from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PaymentStatus
from app.models.mixins import TimestampMixin


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_payments_user_id_idempotency_key"),
        Index("ix_payments_user_id", "user_id"),
        Index("ix_payments_membership_id", "membership_id"),
        Index("ix_payments_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_memberships.id", ondelete="SET NULL"),
        nullable=True,
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("membership_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default=PaymentStatus.SUCCEEDED.value,
        nullable=False,
    )
    mock_reference: Mapped[str] = mapped_column(String(120), nullable=False)

    user = relationship("User", back_populates="payments")
    membership = relationship("UserMembership", back_populates="payments")
    plan = relationship("MembershipPlan", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payment", uselist=False)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("payment_id", name="uq_invoices_payment_id"),
        UniqueConstraint("invoice_number", name="uq_invoices_invoice_number"),
        Index("ix_invoices_user_id", "user_id"),
        Index("ix_invoices_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    invoice_number: Mapped[str] = mapped_column(String(80), nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    plan_name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    membership_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    membership_expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="invoices")
    payment = relationship("Payment", back_populates="invoice")
