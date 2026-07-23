"""localize membership billing to VND

Revision ID: 20260723_0007
Revises: 20260722_0006
Create Date: 2026-07-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260723_0007"
down_revision: str | Sequence[str] | None = "20260722_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE membership_plans
        SET base_price = CASE name
            WHEN '1 Month' THEN 720000
            WHEN '3 Months' THEN 1980000
            WHEN '6 Months' THEN 3600000
            WHEN '1 Year' THEN 6480000
            WHEN '2 Years' THEN 11880000
            WHEN '3 Years' THEN 16200000
            ELSE base_price
        END
        """
    )
    op.execute(
        """
        UPDATE payments
        SET amount = amount * 6000,
            discount_amount = discount_amount * 6000
        WHERE amount < 100000
        """
    )
    op.execute(
        """
        UPDATE invoices
        SET amount = amount * 6000,
            discount_amount = discount_amount * 6000
        WHERE amount < 100000
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE membership_plans
        SET base_price = CASE name
            WHEN '1 Month' THEN 120
            WHEN '3 Months' THEN 330
            WHEN '6 Months' THEN 600
            WHEN '1 Year' THEN 1080
            WHEN '2 Years' THEN 1980
            WHEN '3 Years' THEN 2700
            ELSE base_price
        END
        """
    )
    op.execute(
        """
        UPDATE payments
        SET amount = amount / 6000,
            discount_amount = discount_amount / 6000
        """
    )
    op.execute(
        """
        UPDATE invoices
        SET amount = amount / 6000,
            discount_amount = discount_amount / 6000
        """
    )
