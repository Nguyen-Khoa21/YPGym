"""Extend billing payments for VNPay settlement.

Revision ID: 20260929_0015
Revises: 20260927_0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260929_0015"
down_revision: str | None = "20260927_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_payments_status", "payments", type_="check")
    op.add_column("payments", sa.Column("amount_vnd", sa.BigInteger()))
    op.add_column("payments", sa.Column("provider", sa.String(24), nullable=False, server_default="mock"))
    op.add_column("payments", sa.Column("txn_ref", sa.String(100)))
    op.add_column("payments", sa.Column("currency", sa.String(3), nullable=False, server_default="VND"))
    op.add_column("payments", sa.Column("provider_transaction_no", sa.String(100)))
    op.add_column("payments", sa.Column("response_code", sa.String(10)))
    op.add_column("payments", sa.Column("transaction_status", sa.String(10)))
    op.add_column("payments", sa.Column("bank_code", sa.String(20)))
    op.add_column("payments", sa.Column("card_type", sa.String(20)))
    op.add_column("payments", sa.Column("pay_date", sa.DateTime(timezone=True)))
    op.add_column("payments", sa.Column("paid_at", sa.DateTime(timezone=True)))
    op.add_column("payments", sa.Column("expires_at", sa.DateTime(timezone=True)))
    op.add_column("payments", sa.Column("client_platform", sa.String(16), nullable=False, server_default="web"))
    op.execute("UPDATE payments SET amount_vnd = ROUND(amount)::bigint")
    op.alter_column("payments", "amount_vnd", nullable=False)
    op.create_check_constraint("ck_payments_amount_vnd_positive", "payments", "amount_vnd > 0")
    op.create_check_constraint(
        "ck_payments_status",
        "payments",
        "status IN ('pending', 'paid', 'succeeded', 'failed', 'cancelled', 'expired')",
    )
    op.create_unique_constraint("uq_payments_txn_ref", "payments", ["txn_ref"])
    op.create_index(
        "uq_payments_provider_transaction_no",
        "payments",
        ["provider", "provider_transaction_no"],
        unique=True,
        postgresql_where=sa.text("provider_transaction_no IS NOT NULL"),
    )
    op.create_index("ix_payments_status_expires", "payments", ["status", "expires_at"])


def downgrade() -> None:
    op.drop_index("ix_payments_status_expires", table_name="payments")
    op.drop_index("uq_payments_provider_transaction_no", table_name="payments")
    op.drop_constraint("uq_payments_txn_ref", "payments", type_="unique")
    op.drop_constraint("ck_payments_status", "payments", type_="check")
    op.drop_constraint("ck_payments_amount_vnd_positive", "payments", type_="check")
    op.execute("UPDATE payments SET status = 'succeeded' WHERE status = 'paid'")
    op.execute("UPDATE payments SET status = 'failed' WHERE status IN ('pending', 'cancelled', 'expired')")
    for column in (
        "client_platform", "expires_at", "paid_at", "pay_date", "card_type", "bank_code",
        "transaction_status", "response_code", "provider_transaction_no", "currency", "txn_ref",
        "provider", "amount_vnd",
    ):
        op.drop_column("payments", column)
    op.create_check_constraint("ck_payments_status", "payments", "status IN ('succeeded', 'failed')")
