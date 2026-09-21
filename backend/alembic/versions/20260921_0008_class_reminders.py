"""add class reminder preferences and notification targets

Revision ID: 20260921_0008
Revises: 20260723_0007
Create Date: 2026-09-21
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260921_0008"
down_revision: str | Sequence[str] | None = "20260723_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notification_preferences",
        sa.Column("class_reminders_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column("notifications", sa.Column("action_type", sa.String(length=40), nullable=True))
    op.add_column("notifications", sa.Column("action_id", sa.Uuid(), nullable=True))

    configuration = sa.table(
        "system_configurations",
        sa.column("id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("value", sa.Text()),
        sa.column("value_type", sa.String()),
        sa.column("description", sa.Text()),
    )
    op.execute(
        postgresql.insert(configuration)
        .values(
            id=uuid4(),
            key="class_reminder_lead_minutes",
            value="120",
            value_type="integer",
            description="Lead time for booked-class reminders.",
        )
        .on_conflict_do_nothing(index_elements=["key"]),
    )


def downgrade() -> None:
    op.execute("DELETE FROM system_configurations WHERE key = 'class_reminder_lead_minutes'")
    op.drop_column("notifications", "action_id")
    op.drop_column("notifications", "action_type")
    op.drop_column("notification_preferences", "class_reminders_enabled")
