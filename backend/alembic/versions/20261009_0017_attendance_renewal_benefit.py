"""Add attendance-based membership renewal benefit snapshots.

Revision ID: 20261009_0017
Revises: 20261005_0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0017"
down_revision: str | None = "20261005_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("attendance_benefit_period_start", sa.Date()))
    op.add_column("payments", sa.Column("discount_details", sa.JSON()))
    op.create_check_constraint(
        "ck_payments_attendance_benefit_membership",
        "payments",
        "attendance_benefit_period_start IS NULL OR product_type = 'membership'",
    )
    op.create_index(
        "uq_payments_active_attendance_benefit",
        "payments",
        ["user_id", "attendance_benefit_period_start"],
        unique=True,
        postgresql_where=sa.text(
            "attendance_benefit_period_start IS NOT NULL "
            "AND product_type = 'membership' "
            "AND status IN ('pending', 'paid', 'succeeded')"
        ),
    )
    op.add_column("invoices", sa.Column("discount_details", sa.JSON()))


def downgrade() -> None:
    op.drop_column("invoices", "discount_details")
    op.drop_index("uq_payments_active_attendance_benefit", table_name="payments")
    op.drop_constraint("ck_payments_attendance_benefit_membership", "payments", type_="check")
    op.drop_column("payments", "discount_details")
    op.drop_column("payments", "attendance_benefit_period_start")
