from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


DISTRICT_1_GYM_ID = UUID("1e9418c3-9674-54fe-b0b5-ebb6cec6bb8d")
DISTRICT_11_GYM_ID = UUID("613dfe59-c0c6-5cef-b991-8be72918409c")
DEFAULT_GYM_TIMEZONE = "Asia/Ho_Chi_Minh"


class GymLocation(TimestampMixin, Base):
    __tablename__ = "gym_locations"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_gym_locations_capacity_positive"),
        Index("ix_gym_locations_is_active", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=DEFAULT_GYM_TIMEZONE,
        server_default=DEFAULT_GYM_TIMEZONE,
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class WorkforceGymAssignment(TimestampMixin, Base):
    __tablename__ = "workforce_gym_assignments"
    __table_args__ = (
        CheckConstraint(
            "assigned_role IN ('manager', 'staff', 'pt')",
            name="ck_workforce_gym_assignments_role",
        ),
        Index("ix_workforce_gym_assignments_gym_role", "gym_id", "assigned_role", "is_active"),
        Index(
            "uq_workforce_gym_assignments_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    gym_id: Mapped[UUID] = mapped_column(ForeignKey("gym_locations.id", ondelete="RESTRICT"), nullable=False)
    assigned_role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
