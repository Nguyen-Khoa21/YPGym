from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PaymentStatus
from app.models.mixins import TimestampMixin


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_payments_user_id_idempotency_key"),
        UniqueConstraint("txn_ref", name="uq_payments_txn_ref"),
        CheckConstraint("amount_vnd > 0", name="ck_payments_amount_vnd_positive"),
        CheckConstraint(
            "status IN ('pending', 'paid', 'succeeded', 'failed', 'cancelled', 'expired', 'paid_review')",
            name="ck_payments_status",
        ),
        CheckConstraint("product_type IN ('membership', 'class_booking')", name="ck_payments_product_type"),
        CheckConstraint(
            "(product_type = 'membership' AND plan_id IS NOT NULL AND class_booking_id IS NULL) OR "
            "(product_type = 'class_booking' AND plan_id IS NULL AND class_booking_id IS NOT NULL)",
            name="ck_payments_product_reference",
        ),
        CheckConstraint(
            "attendance_benefit_period_start IS NULL OR product_type = 'membership'",
            name="ck_payments_attendance_benefit_membership",
        ),
        Index("ix_payments_user_id", "user_id"),
        Index("ix_payments_membership_id", "membership_id"),
        Index("ix_payments_class_booking_id", "class_booking_id"),
        Index("ix_payments_product_type", "product_type"),
        Index("ix_payments_created_at", "created_at"),
        Index("ix_payments_status_expires", "status", "expires_at"),
        Index(
            "uq_payments_provider_transaction_no",
            "provider",
            "provider_transaction_no",
            unique=True,
            postgresql_where=text("provider_transaction_no IS NOT NULL"),
        ),
        Index(
            "uq_payments_active_attendance_benefit",
            "user_id",
            "attendance_benefit_period_start",
            unique=True,
            postgresql_where=text(
                "attendance_benefit_period_start IS NOT NULL "
                "AND product_type = 'membership' "
                "AND status IN ('pending', 'paid', 'succeeded')"
            ),
        ),
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
    plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("membership_plans.id", ondelete="RESTRICT"),
        nullable=True,
    )
    class_booking_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("class_bookings.id", ondelete="RESTRICT"),
    )
    product_type: Mapped[str] = mapped_column(String(24), nullable=False, default="membership")
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount_vnd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default=PaymentStatus.SUCCEEDED.value,
        nullable=False,
    )
    mock_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(24), nullable=False, default="mock")
    txn_ref: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="VND")
    provider_transaction_no: Mapped[str | None] = mapped_column(String(100))
    response_code: Mapped[str | None] = mapped_column(String(10))
    transaction_status: Mapped[str | None] = mapped_column(String(10))
    bank_code: Mapped[str | None] = mapped_column(String(20))
    card_type: Mapped[str | None] = mapped_column(String(20))
    pay_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    client_platform: Mapped[str] = mapped_column(String(16), nullable=False, default="web")
    attendance_benefit_period_start: Mapped[date | None] = mapped_column(Date)
    discount_details: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    user = relationship("User", back_populates="payments")
    membership = relationship("UserMembership", back_populates="payments")
    plan = relationship("MembershipPlan", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payment", uselist=False)
    class_booking = relationship("ClassBooking", foreign_keys=[class_booking_id])


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("payment_id", name="uq_invoices_payment_id"),
        UniqueConstraint("invoice_number", name="uq_invoices_invoice_number"),
        CheckConstraint("product_type IN ('membership', 'class_booking')", name="ck_invoices_product_type"),
        Index("ix_invoices_user_id", "user_id"),
        Index("ix_invoices_created_at", "created_at"),
        Index(
            "uq_invoices_class_booking_id",
            "class_booking_id",
            unique=True,
            postgresql_where=text("class_booking_id IS NOT NULL"),
        ),
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
    class_booking_id: Mapped[UUID | None] = mapped_column(ForeignKey("class_bookings.id", ondelete="RESTRICT"))
    product_type: Mapped[str] = mapped_column(String(24), nullable=False, default="membership")
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    membership_start_date: Mapped[date | None] = mapped_column(Date)
    membership_expiry_date: Mapped[date | None] = mapped_column(Date)
    service_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    service_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discount_details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="invoices")
    payment = relationship("Payment", back_populates="invoice")
