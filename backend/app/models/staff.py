from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.gym import DISTRICT_1_GYM_ID
from app.models.mixins import TimestampMixin


class StaffShift(TimestampMixin, Base):
    __tablename__ = "staff_shifts"
    __table_args__ = (
        CheckConstraint(
            "clocked_out_at IS NULL OR clocked_out_at > clocked_in_at",
            name="ck_staff_shifts_time_order",
        ),
        Index("ix_staff_shifts_user_clocked_in", "user_id", "clocked_in_at"),
        Index("ix_staff_shifts_clocked_in_at", "clocked_in_at"),
        Index("ix_staff_shifts_gym_user_time", "gym_id", "user_id", "clocked_in_at"),
        Index(
            "uq_staff_shifts_open_user",
            "user_id",
            unique=True,
            postgresql_where=text("clocked_out_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey("gym_locations.id", ondelete="RESTRICT"),
        nullable=False,
        default=DISTRICT_1_GYM_ID,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    clocked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clocked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
