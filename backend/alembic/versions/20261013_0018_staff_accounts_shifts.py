"""Add staff first-login state and auditable shifts.

Revision ID: 20261013_0018
Revises: 20261009_0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261013_0018"
down_revision: str | Sequence[str] | None = "20261009_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_table(
        "staff_shifts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("clocked_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clocked_out_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "clocked_out_at IS NULL OR clocked_out_at > clocked_in_at",
            name="ck_staff_shifts_time_order",
        ),
    )
    op.create_index("ix_staff_shifts_user_clocked_in", "staff_shifts", ["user_id", "clocked_in_at"])
    op.create_index("ix_staff_shifts_clocked_in_at", "staff_shifts", ["clocked_in_at"])
    op.create_index(
        "uq_staff_shifts_open_user",
        "staff_shifts",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("clocked_out_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_staff_shifts_open_user", table_name="staff_shifts")
    op.drop_index("ix_staff_shifts_clocked_in_at", table_name="staff_shifts")
    op.drop_index("ix_staff_shifts_user_clocked_in", table_name="staff_shifts")
    op.drop_table("staff_shifts")
    op.drop_column("users", "must_change_password")
