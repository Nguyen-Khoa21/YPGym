"""Scope membership and class payments to gym locations.

Revision ID: 20261109_0021
Revises: 20261107_0020
"""

from alembic import op
import sqlalchemy as sa


revision = "20261109_0021"
down_revision = "20261107_0020"
branch_labels = None
depends_on = None

DISTRICT_1_ID = "1e9418c3-9674-54fe-b0b5-ebb6cec6bb8d"


def upgrade() -> None:
    op.add_column("payments", sa.Column("gym_id", sa.Uuid()))
    op.execute(
        sa.text(
            """
            UPDATE payments AS payment
            SET gym_id = membership.home_gym_id
            FROM user_memberships AS membership
            WHERE payment.membership_id = membership.id
              AND payment.gym_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE payments AS payment
            SET gym_id = gym_class.gym_id
            FROM class_bookings AS booking
            JOIN classes AS gym_class ON gym_class.id = booking.class_id
            WHERE payment.class_booking_id = booking.id
              AND payment.gym_id IS NULL
            """
        )
    )
    op.execute(
        sa.text("UPDATE payments SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL").bindparams(
            gym_id=DISTRICT_1_ID,
        )
    )
    op.alter_column("payments", "gym_id", nullable=False)
    op.create_foreign_key(
        "fk_payments_gym_id_gym_locations",
        "payments",
        "gym_locations",
        ["gym_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_payments_gym_created_at", "payments", ["gym_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_payments_gym_created_at", table_name="payments")
    op.drop_constraint("fk_payments_gym_id_gym_locations", "payments", type_="foreignkey")
    op.drop_column("payments", "gym_id")
