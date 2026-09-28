from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ExternalIdentity(TimestampMixin, Base):
    __tablename__ = "external_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_external_identities_subject"),
        UniqueConstraint("user_id", "provider", name="uq_external_identities_user_provider"),
        Index("ix_external_identities_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(24), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(255))
    provider_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OAuthPendingLink(TimestampMixin, Base):
    __tablename__ = "oauth_pending_links"
    __table_args__ = (
        UniqueConstraint("code_hash", name="uq_oauth_pending_links_code_hash"),
        UniqueConstraint("email_token_hash", name="uq_oauth_pending_links_email_token_hash"),
        Index("ix_oauth_pending_links_user_id", "user_id"),
        Index("ix_oauth_pending_links_email_due", "email_delivery_state", "email_next_attempt_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(24), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str] = mapped_column(String(255), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    email_token_hash: Mapped[str | None] = mapped_column(String(64))
    correlation_id: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    link_method: Mapped[str | None] = mapped_column(String(24))
    password_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    email_delivery_state: Mapped[str] = mapped_column(String(24), nullable=False, default="idle", server_default="idle")
    email_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    email_next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_error_code: Mapped[str | None] = mapped_column(String(64))
