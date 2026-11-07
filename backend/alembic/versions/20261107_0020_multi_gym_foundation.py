"""Add gym locations, workforce assignments, and legacy location backfill.

Revision ID: 20261107_0020
Revises: 20261103_0019
"""

from alembic import op
import sqlalchemy as sa


revision = "20261107_0020"
down_revision = "20261103_0019"
branch_labels = None
depends_on = None

DISTRICT_1_ID = "1e9418c3-9674-54fe-b0b5-ebb6cec6bb8d"
DISTRICT_11_ID = "613dfe59-c0c6-5cef-b991-8be72918409c"


def upgrade() -> None:
    op.create_table(
        "gym_locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("timezone", sa.String(64), server_default="Asia/Ho_Chi_Minh", nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("capacity > 0", name="ck_gym_locations_capacity_positive"),
    )
    op.create_index("ix_gym_locations_is_active", "gym_locations", ["is_active"])
    op.execute(
        sa.text(
            """
            INSERT INTO gym_locations (id, name, slug, district, address, timezone, capacity, is_active)
            VALUES
                (CAST(:district_1_id AS uuid), 'YPGym District 1', 'district-1', 'District 1',
                 'District 1, Ho Chi Minh City', 'Asia/Ho_Chi_Minh',
                 COALESCE((SELECT NULLIF(value, '')::integer FROM system_configurations WHERE key = 'gym_capacity'), 150), true),
                (CAST(:district_11_id AS uuid), 'YPGym District 11', 'district-11', 'District 11',
                 'District 11, Ho Chi Minh City', 'Asia/Ho_Chi_Minh',
                 COALESCE((SELECT NULLIF(value, '')::integer FROM system_configurations WHERE key = 'gym_capacity'), 150), true)
            """
        ).bindparams(district_1_id=DISTRICT_1_ID, district_11_id=DISTRICT_11_ID)
    )

    op.create_table(
        "workforce_gym_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gym_id", sa.Uuid(), sa.ForeignKey("gym_locations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "assigned_role IN ('manager', 'staff', 'pt')",
            name="ck_workforce_gym_assignments_role",
        ),
    )
    op.create_index(
        "ix_workforce_gym_assignments_gym_role",
        "workforce_gym_assignments",
        ["gym_id", "assigned_role", "is_active"],
    )
    op.create_index(
        "uq_workforce_gym_assignments_active_user",
        "workforce_gym_assignments",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO workforce_gym_assignments (id, user_id, gym_id, assigned_role, is_active)
            SELECT id, id, CAST(:district_1_id AS uuid), role, true
            FROM users
            WHERE role IN ('manager', 'staff', 'pt')
            """
        ).bindparams(district_1_id=DISTRICT_1_ID)
    )

    _add_required_gym_column("iot_devices", "gym_id")
    _add_required_gym_column("attendance_sessions", "gym_id")
    _add_required_gym_column("attendance_events", "gym_id")
    _add_required_gym_column("user_memberships", "home_gym_id")
    _add_required_gym_column("classes", "gym_id")
    _add_required_gym_column("staff_shifts", "gym_id")
    op.add_column("broadcast_announcements", sa.Column("gym_id", sa.Uuid()))
    op.execute(
        sa.text("UPDATE broadcast_announcements SET gym_id = CAST(:gym_id AS uuid)").bindparams(
            gym_id=DISTRICT_1_ID
        )
    )

    _create_gym_foreign_key("iot_devices", "gym_id")
    _create_gym_foreign_key("attendance_sessions", "gym_id")
    _create_gym_foreign_key("attendance_events", "gym_id")
    _create_gym_foreign_key("user_memberships", "home_gym_id")
    _create_gym_foreign_key("classes", "gym_id")
    _create_gym_foreign_key("staff_shifts", "gym_id")
    _create_gym_foreign_key("broadcast_announcements", "gym_id")

    op.create_index("ix_iot_devices_gym_active", "iot_devices", ["gym_id", "is_active"])
    op.create_index("ix_attendance_sessions_gym_status", "attendance_sessions", ["gym_id", "status"])
    op.create_index(
        "ix_attendance_events_gym_type_at",
        "attendance_events",
        ["gym_id", "event_type", "event_at"],
    )
    op.create_index(
        "ix_user_memberships_home_gym_status",
        "user_memberships",
        ["home_gym_id", "status"],
    )
    op.create_index("ix_classes_gym_start", "classes", ["gym_id", "start_at"])
    op.create_index(
        "ix_staff_shifts_gym_user_time",
        "staff_shifts",
        ["gym_id", "user_id", "clocked_in_at"],
    )
    op.create_index(
        "ix_broadcast_announcements_gym_active_period",
        "broadcast_announcements",
        ["gym_id", "is_active", "starts_at", "ends_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_broadcast_announcements_gym_active_period", table_name="broadcast_announcements")
    op.drop_index("ix_staff_shifts_gym_user_time", table_name="staff_shifts")
    op.drop_index("ix_classes_gym_start", table_name="classes")
    op.drop_index("ix_user_memberships_home_gym_status", table_name="user_memberships")
    op.drop_index("ix_attendance_events_gym_type_at", table_name="attendance_events")
    op.drop_index("ix_attendance_sessions_gym_status", table_name="attendance_sessions")
    op.drop_index("ix_iot_devices_gym_active", table_name="iot_devices")

    for table, column in (
        ("broadcast_announcements", "gym_id"),
        ("staff_shifts", "gym_id"),
        ("classes", "gym_id"),
        ("user_memberships", "home_gym_id"),
        ("attendance_events", "gym_id"),
        ("attendance_sessions", "gym_id"),
        ("iot_devices", "gym_id"),
    ):
        op.drop_constraint(f"fk_{table}_{column}_gym_locations", table, type_="foreignkey")
        op.drop_column(table, column)

    op.drop_index("uq_workforce_gym_assignments_active_user", table_name="workforce_gym_assignments")
    op.drop_index("ix_workforce_gym_assignments_gym_role", table_name="workforce_gym_assignments")
    op.drop_table("workforce_gym_assignments")
    op.drop_index("ix_gym_locations_is_active", table_name="gym_locations")
    op.drop_table("gym_locations")


def _add_required_gym_column(table: str, column: str) -> None:
    op.add_column(table, sa.Column(column, sa.Uuid()))
    op.execute(
        sa.text(f"UPDATE {table} SET {column} = CAST(:gym_id AS uuid)").bindparams(
            gym_id=DISTRICT_1_ID
        )
    )
    op.alter_column(table, column, nullable=False)


def _create_gym_foreign_key(table: str, column: str) -> None:
    op.create_foreign_key(
        f"fk_{table}_{column}_gym_locations",
        table,
        "gym_locations",
        [column],
        ["id"],
        ondelete="RESTRICT",
    )
