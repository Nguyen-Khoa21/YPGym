from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class EmailDelivery(TimestampMixin, Base):
    __tablename__ = "email_deliveries"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_email_deliveries_idempotency_key"),
        Index("ix_email_deliveries_due", "status", "next_attempt_at", "created_at"),
        Index("ix_email_deliveries_user_id", "user_id"),
        Index("ix_email_deliveries_invoice_id", "invoice_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(String(64), nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(ForeignKey("user_memberships.id", ondelete="CASCADE"), nullable=False)
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_masked: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", server_default="queued")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_to_provider_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_category: Mapped[str | None] = mapped_column(String(32))
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
