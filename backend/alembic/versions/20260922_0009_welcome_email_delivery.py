"""add welcome email delivery attempts

Revision ID: 20260922_0009
Revises: 20260921_0008
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260922_0009"
down_revision: str | Sequence[str] | None = "20260921_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("delivery_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "notifications",
        sa.Column("last_delivery_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notifications_email_delivery",
        "notifications",
        ["notification_type", "channel", "delivery_state", "last_delivery_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_email_delivery", table_name="notifications")
    op.drop_column("notifications", "last_delivery_attempt_at")
    op.drop_column("notifications", "delivery_attempts")
