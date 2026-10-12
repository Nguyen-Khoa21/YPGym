"""Add independently paid class bookings.

Revision ID: 20261005_0016
Revises: 20260929_0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261005_0016"
down_revision: str | None = "20260929_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("classes", sa.Column("price_vnd", sa.BigInteger()))
    op.create_check_constraint("ck_classes_price_vnd_positive", "classes", "price_vnd IS NULL OR price_vnd > 0")

    op.drop_constraint("ck_class_bookings_status", "class_bookings", type_="check")
    op.execute("UPDATE class_bookings SET status = 'confirmed' WHERE status = 'booked'")
    op.add_column("class_bookings", sa.Column("price_vnd", sa.BigInteger()))
    op.add_column("class_bookings", sa.Column("entitlement_source", sa.String(16), nullable=False, server_default="legacy"))
    op.add_column("class_bookings", sa.Column("current_payment_id", sa.Uuid()))
    op.add_column("class_bookings", sa.Column("reserved_until", sa.DateTime(timezone=True)))
    op.add_column("class_bookings", sa.Column("confirmed_at", sa.DateTime(timezone=True)))
    op.add_column("class_bookings", sa.Column("cancelled_at", sa.DateTime(timezone=True)))
    op.add_column("class_bookings", sa.Column("cancellation_reason", sa.Text()))
    op.add_column("class_bookings", sa.Column("refund_status", sa.String(16), nullable=False, server_default="none"))
    op.add_column("class_bookings", sa.Column("attended_at", sa.DateTime(timezone=True)))
    op.add_column("class_bookings", sa.Column("checked_in_by_id", sa.Uuid()))
    op.execute("UPDATE class_bookings SET confirmed_at = created_at WHERE status = 'confirmed'")
    op.create_check_constraint("ck_class_bookings_price_vnd_positive", "class_bookings", "price_vnd IS NULL OR price_vnd > 0")
    op.create_check_constraint(
        "ck_class_bookings_status",
        "class_bookings",
        "status IN ('pending_payment', 'confirmed', 'cancelled', 'expired', 'payment_failed', 'refunded')",
    )
    op.create_check_constraint(
        "ck_class_bookings_entitlement_source",
        "class_bookings",
        "entitlement_source IN ('legacy', 'paid')",
    )
    op.create_check_constraint(
        "ck_class_bookings_refund_status",
        "class_bookings",
        "refund_status IN ('none', 'required', 'resolved')",
    )
    op.create_foreign_key(
        "fk_class_bookings_checked_in_by_id_users",
        "class_bookings",
        "users",
        ["checked_in_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint("ck_payments_status", "payments", type_="check")
    op.add_column("payments", sa.Column("product_type", sa.String(24), nullable=False, server_default="membership"))
    op.add_column("payments", sa.Column("class_booking_id", sa.Uuid()))
    op.alter_column("payments", "plan_id", existing_type=sa.Uuid(), nullable=True)
    op.create_foreign_key(
        "fk_payments_class_booking_id_class_bookings",
        "payments",
        "class_bookings",
        ["class_booking_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_payments_class_booking_id", "payments", ["class_booking_id"])
    op.create_index("ix_payments_product_type", "payments", ["product_type"])
    op.create_check_constraint(
        "ck_payments_status",
        "payments",
        "status IN ('pending', 'paid', 'succeeded', 'failed', 'cancelled', 'expired', 'paid_review')",
    )
    op.create_check_constraint("ck_payments_product_type", "payments", "product_type IN ('membership', 'class_booking')")
    op.create_check_constraint(
        "ck_payments_product_reference",
        "payments",
        "(product_type = 'membership' AND plan_id IS NOT NULL AND class_booking_id IS NULL) OR "
        "(product_type = 'class_booking' AND plan_id IS NULL AND class_booking_id IS NOT NULL)",
    )
    op.create_foreign_key(
        "fk_class_bookings_current_payment_id_payments",
        "class_bookings",
        "payments",
        ["current_payment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_class_bookings_current_payment_id",
        "class_bookings",
        ["current_payment_id"],
        unique=True,
        postgresql_where=sa.text("current_payment_id IS NOT NULL"),
    )

    op.add_column("invoices", sa.Column("class_booking_id", sa.Uuid()))
    op.add_column("invoices", sa.Column("product_type", sa.String(24), nullable=False, server_default="membership"))
    op.add_column("invoices", sa.Column("product_name", sa.String(160)))
    op.add_column("invoices", sa.Column("service_start_at", sa.DateTime(timezone=True)))
    op.add_column("invoices", sa.Column("service_end_at", sa.DateTime(timezone=True)))
    op.execute("UPDATE invoices SET product_name = plan_name")
    op.alter_column("invoices", "product_name", nullable=False)
    op.alter_column("invoices", "membership_start_date", existing_type=sa.Date(), nullable=True)
    op.alter_column("invoices", "membership_expiry_date", existing_type=sa.Date(), nullable=True)
    op.create_foreign_key(
        "fk_invoices_class_booking_id_class_bookings",
        "invoices",
        "class_bookings",
        ["class_booking_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint("ck_invoices_product_type", "invoices", "product_type IN ('membership', 'class_booking')")
    op.create_index(
        "uq_invoices_class_booking_id",
        "invoices",
        ["class_booking_id"],
        unique=True,
        postgresql_where=sa.text("class_booking_id IS NOT NULL"),
    )

    op.alter_column("email_deliveries", "membership_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("email_deliveries", sa.Column("class_booking_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_email_deliveries_class_booking_id_class_bookings",
        "email_deliveries",
        "class_bookings",
        ["class_booking_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_email_deliveries_class_booking_id", "email_deliveries", ["class_booking_id"])
    op.create_check_constraint(
        "ck_email_deliveries_product_reference",
        "email_deliveries",
        "num_nonnulls(membership_id, class_booking_id) = 1",
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM payments WHERE product_type = 'class_booking') THEN
                RAISE EXCEPTION 'Cannot downgrade while paid class-booking transactions exist';
            END IF;
        END $$;
        """
    )
    op.drop_constraint("ck_email_deliveries_product_reference", "email_deliveries", type_="check")
    op.drop_index("ix_email_deliveries_class_booking_id", table_name="email_deliveries")
    op.drop_constraint("fk_email_deliveries_class_booking_id_class_bookings", "email_deliveries", type_="foreignkey")
    op.drop_column("email_deliveries", "class_booking_id")
    op.alter_column("email_deliveries", "membership_id", existing_type=sa.Uuid(), nullable=False)

    op.drop_index("uq_invoices_class_booking_id", table_name="invoices")
    op.drop_constraint("ck_invoices_product_type", "invoices", type_="check")
    op.drop_constraint("fk_invoices_class_booking_id_class_bookings", "invoices", type_="foreignkey")
    op.alter_column("invoices", "membership_expiry_date", existing_type=sa.Date(), nullable=False)
    op.alter_column("invoices", "membership_start_date", existing_type=sa.Date(), nullable=False)
    for column in ("service_end_at", "service_start_at", "product_name", "product_type", "class_booking_id"):
        op.drop_column("invoices", column)

    op.drop_index("uq_class_bookings_current_payment_id", table_name="class_bookings")
    op.drop_constraint("fk_class_bookings_current_payment_id_payments", "class_bookings", type_="foreignkey")
    op.drop_constraint("ck_payments_product_reference", "payments", type_="check")
    op.drop_constraint("ck_payments_product_type", "payments", type_="check")
    op.drop_constraint("ck_payments_status", "payments", type_="check")
    op.drop_index("ix_payments_product_type", table_name="payments")
    op.drop_index("ix_payments_class_booking_id", table_name="payments")
    op.drop_constraint("fk_payments_class_booking_id_class_bookings", "payments", type_="foreignkey")
    op.drop_column("payments", "class_booking_id")
    op.drop_column("payments", "product_type")
    op.alter_column("payments", "plan_id", existing_type=sa.Uuid(), nullable=False)
    op.create_check_constraint(
        "ck_payments_status",
        "payments",
        "status IN ('pending', 'paid', 'succeeded', 'failed', 'cancelled', 'expired')",
    )

    op.execute("UPDATE class_bookings SET status = 'booked' WHERE status = 'confirmed'")
    op.execute("UPDATE class_bookings SET status = 'cancelled' WHERE status NOT IN ('booked', 'cancelled')")
    op.drop_constraint("fk_class_bookings_checked_in_by_id_users", "class_bookings", type_="foreignkey")
    op.drop_constraint("ck_class_bookings_refund_status", "class_bookings", type_="check")
    op.drop_constraint("ck_class_bookings_entitlement_source", "class_bookings", type_="check")
    op.drop_constraint("ck_class_bookings_status", "class_bookings", type_="check")
    op.drop_constraint("ck_class_bookings_price_vnd_positive", "class_bookings", type_="check")
    for column in (
        "checked_in_by_id", "attended_at", "refund_status", "cancellation_reason", "cancelled_at",
        "confirmed_at", "reserved_until", "current_payment_id", "entitlement_source", "price_vnd",
    ):
        op.drop_column("class_bookings", column)
    op.create_check_constraint("ck_class_bookings_status", "class_bookings", "status IN ('booked', 'cancelled')")

    op.drop_constraint("ck_classes_price_vnd_positive", "classes", type_="check")
    op.drop_column("classes", "price_vnd")
