"""Record how a user registered and who registered them in person.

Revision ID: 20261110_0024
Revises: 20261110_0023
"""

from alembic import op
import sqlalchemy as sa


revision = "20261110_0024"
down_revision = "20261110_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("registration_channel", sa.String(length=16), server_default="online", nullable=False))
    op.add_column("users", sa.Column("registered_by_user_id", sa.Uuid(), nullable=True))
    op.create_check_constraint(
        "ck_users_registration_channel",
        "users",
        "registration_channel IN ('online', 'in_person')",
    )
    op.create_foreign_key(
        "fk_users_registered_by_user_id_users",
        "users",
        "users",
        ["registered_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_registered_by_user_id_users", "users", type_="foreignkey")
    op.drop_constraint("ck_users_registration_channel", "users", type_="check")
    op.drop_column("users", "registered_by_user_id")
    op.drop_column("users", "registration_channel")
