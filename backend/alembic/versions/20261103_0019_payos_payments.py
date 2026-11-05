"""Add payOS payment-link identifiers while preserving historical providers.

Revision ID: 20261103_0019
Revises: 20261013_0018
"""

from alembic import op
import sqlalchemy as sa


revision = "20261103_0019"
down_revision = "20261013_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE payos_order_code_seq AS BIGINT START WITH 1000000000")
    op.add_column("payments", sa.Column("payos_order_code", sa.BigInteger()))
    op.add_column("payments", sa.Column("payment_link_id", sa.String(100)))
    op.add_column("payments", sa.Column("checkout_url", sa.String(2048)))
    op.create_index(
        "uq_payments_payos_order_code",
        "payments",
        ["payos_order_code"],
        unique=True,
        postgresql_where=sa.text("payos_order_code IS NOT NULL"),
    )
    op.create_index(
        "uq_payments_payment_link_id",
        "payments",
        ["payment_link_id"],
        unique=True,
        postgresql_where=sa.text("payment_link_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_payments_payment_link_id", table_name="payments")
    op.drop_index("uq_payments_payos_order_code", table_name="payments")
    op.drop_column("payments", "checkout_url")
    op.drop_column("payments", "payment_link_id")
    op.drop_column("payments", "payos_order_code")
    op.execute("DROP SEQUENCE payos_order_code_seq")
