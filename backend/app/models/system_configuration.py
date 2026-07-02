from uuid import UUID, uuid4

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SystemConfigurationValueType
from app.models.mixins import TimestampMixin


class SystemConfiguration(TimestampMixin, Base):
    __tablename__ = "system_configurations"
    __table_args__ = (
        UniqueConstraint("key", name="uq_system_configurations_key"),
        Index("ix_system_configurations_key", "key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(
        String(32),
        default=SystemConfigurationValueType.STRING.value,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
