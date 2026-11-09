"""Add short one-time codes to email verifications.

Revision ID: 20261110_0022
Revises: 20261109_0021
"""

from alembic import op
import sqlalchemy as sa


revision = "20261110_0022"
down_revision = "20261109_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("email_verifications", sa.Column("code_hash", sa.String(length=128), nullable=True))
    op.add_column(
        "email_verifications",
        sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("email_verifications", "failed_attempts")
    op.drop_column("email_verifications", "code_hash")
