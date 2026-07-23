"""add trainer profile details

Revision ID: 20260722_0006
Revises: 20260716_0005
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0006"
down_revision: str | Sequence[str] | None = "20260716_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("personal_trainers", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column(
        "personal_trainers",
        sa.Column("availability_summary", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("personal_trainers", "availability_summary")
    op.drop_column("personal_trainers", "bio")
