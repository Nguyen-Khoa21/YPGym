"""Add secure pending OAuth account links.

Revision ID: 20260927_0014
Revises: 20260926_0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260927_0014"
down_revision: str | None = "20260926_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oauth_pending_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("provider_subject", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(255), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("email_token_hash", sa.String(64)),
        sa.Column("correlation_id", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("link_method", sa.String(24)),
        sa.Column("password_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("email_delivery_state", sa.String(24), nullable=False, server_default="idle"),
        sa.Column("email_attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("email_next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("email_last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("email_sent_at", sa.DateTime(timezone=True)),
        sa.Column("email_error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash", name="uq_oauth_pending_links_code_hash"),
        sa.UniqueConstraint("email_token_hash", name="uq_oauth_pending_links_email_token_hash"),
    )
    op.create_index("ix_oauth_pending_links_user_id", "oauth_pending_links", ["user_id"])
    op.create_index(
        "ix_oauth_pending_links_email_due",
        "oauth_pending_links",
        ["email_delivery_state", "email_next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_oauth_pending_links_email_due", table_name="oauth_pending_links")
    op.drop_index("ix_oauth_pending_links_user_id", table_name="oauth_pending_links")
    op.drop_table("oauth_pending_links")
