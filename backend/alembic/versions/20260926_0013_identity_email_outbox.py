"""add external identities and membership email outbox

Revision ID: 20260926_0013
Revises: 20260924_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0013"
down_revision: str | Sequence[str] | None = "20260924_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "phone", existing_type=sa.String(32), nullable=True)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    op.create_table(
        "external_identities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("provider_subject", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(255)),
        sa.Column("provider_email_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "provider_subject", name="uq_external_identities_subject"),
        sa.UniqueConstraint("user_id", "provider", name="uq_external_identities_user_provider"),
    )
    op.create_index("ix_external_identities_user_id", "external_identities", ["user_id"])
    op.create_table(
        "email_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("template_type", sa.String(64), nullable=False),
        sa.Column("template_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("membership_id", sa.Uuid(), sa.ForeignKey("user_memberships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_id", sa.Uuid(), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_email", sa.String(255), nullable=False),
        sa.Column("recipient_masked", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), server_default="queued", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("sent_to_provider_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_category", sa.String(32)),
        sa.Column("last_error_code", sa.String(64)),
        sa.Column("provider_message_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_email_deliveries_idempotency_key"),
    )
    op.create_index("ix_email_deliveries_due", "email_deliveries", ["status", "next_attempt_at", "created_at"])
    op.create_index("ix_email_deliveries_user_id", "email_deliveries", ["user_id"])
    op.create_index("ix_email_deliveries_invoice_id", "email_deliveries", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_email_deliveries_invoice_id", table_name="email_deliveries")
    op.drop_index("ix_email_deliveries_user_id", table_name="email_deliveries")
    op.drop_index("ix_email_deliveries_due", table_name="email_deliveries")
    op.drop_table("email_deliveries")
    op.drop_index("ix_external_identities_user_id", table_name="external_identities")
    op.drop_table("external_identities")
    # Provider-only users cannot satisfy the legacy required password/phone columns.
    op.execute("DELETE FROM users WHERE password_hash IS NULL OR phone IS NULL")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.alter_column("users", "phone", existing_type=sa.String(32), nullable=False)
