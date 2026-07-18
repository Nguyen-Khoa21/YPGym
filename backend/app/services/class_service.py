from datetime import UTC, datetime
from math import ceil
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, ResourceNotFoundError
from app.models.classes import GymClass
from app.models.user import User
from app.repositories.class_repository import ClassRepository
from app.repositories.operations_repository import AuditRepository
from app.schemas.class_schema import (
    ClassCancel,
    ClassCreate,
    ClassItem,
    ClassPage,
    ClassUpdate,
    TrainerItem,
)
from app.schemas.operations_schema import PageInfo


def validate_class_times(start_at: datetime, end_at: datetime, *, allow_past: bool = False) -> None:
    if start_at.tzinfo is None or end_at.tzinfo is None:
        raise AppError("CLASS_TIMEZONE_REQUIRED", "Class times must include a timezone.", 422)
    if end_at <= start_at:
        raise AppError("CLASS_TIME_INVALID", "Class end time must be after its start time.", 422)
    if not allow_past and start_at <= datetime.now(UTC):
        raise AppError("CLASS_START_IN_PAST", "New or rescheduled classes must start in the future.", 422)


class ClassService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.classes = ClassRepository(session)
        self.audit = AuditRepository(session)

    async def list_trainers(self) -> list[TrainerItem]:
        return [
            TrainerItem(
                id=item.id,
                display_name=item.display_name,
                specialty=item.specialty,
                is_active=item.is_active,
            )
            for item in await self.classes.list_trainers()
        ]

    async def list_classes(self, **filters) -> ClassPage:
        rows, total, scheduled, cancelled = await self.classes.list_classes(**filters)
        return ClassPage(
            items=[self._item(item, trainer_name) for item, trainer_name in rows],
            page=PageInfo(
                page=filters["page"],
                page_size=filters["page_size"],
                total=total,
                pages=ceil(total / filters["page_size"]) if total else 0,
            ),
            scheduled_count=scheduled,
            cancelled_count=cancelled,
        )

    async def create(self, *, actor: User, payload: ClassCreate) -> ClassItem:
        validate_class_times(payload.start_at, payload.end_at)
        trainer_name = await self._trainer_name(payload.trainer_id)
        await self._ensure_no_overlap(
            start_at=payload.start_at,
            end_at=payload.end_at,
            location=payload.location,
            trainer_id=payload.trainer_id,
        )
        item = await self.classes.create_class(**payload.model_dump(), status="scheduled")
        await self.audit.create(
            actor_user_id=actor.id,
            action="class.created",
            entity_type="class",
            entity_id=str(item.id),
            reason="Class schedule creation",
            outcome="scheduled",
            summary=f"Class '{item.title}' was scheduled.",
            after_data=self._audit_data(item),
        )
        await self.session.commit()
        await self.session.refresh(item)
        return self._item(item, trainer_name)

    async def update(self, *, class_id: UUID, actor: User, payload: ClassUpdate) -> ClassItem:
        item = await self.classes.get_class(class_id, for_update=True)
        if not item:
            raise ResourceNotFoundError("Class was not found.")
        if item.status != "scheduled":
            raise ConflictError("Only scheduled classes can be edited.")
        before = self._audit_data(item)
        changes = payload.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(item, key, value)
        validate_class_times(item.start_at, item.end_at)
        trainer_name = await self._trainer_name(item.trainer_id)
        await self._ensure_no_overlap(
            start_at=item.start_at,
            end_at=item.end_at,
            location=item.location,
            trainer_id=item.trainer_id,
            exclude_id=item.id,
        )
        await self.audit.create(
            actor_user_id=actor.id,
            action="class.updated",
            entity_type="class",
            entity_id=str(item.id),
            reason="Class schedule update",
            outcome="scheduled",
            summary=f"Class '{item.title}' was updated.",
            before_data=before,
            after_data=self._audit_data(item),
        )
        await self.session.commit()
        await self.session.refresh(item)
        return self._item(item, trainer_name)

    async def cancel(self, *, class_id: UUID, actor: User, payload: ClassCancel) -> ClassItem:
        item = await self.classes.get_class(class_id, for_update=True)
        if not item:
            raise ResourceNotFoundError("Class was not found.")
        trainer_name = await self._trainer_name(item.trainer_id, require_active=False)
        if item.status == "cancelled":
            return self._item(item, trainer_name)
        if item.status != "scheduled":
            raise ConflictError("Only scheduled classes can be cancelled.")
        before = self._audit_data(item)
        item.status = "cancelled"
        item.cancellation_reason = payload.reason.strip()
        item.cancelled_by_id = actor.id
        item.cancelled_at = datetime.now(UTC)
        await self.audit.create(
            actor_user_id=actor.id,
            action="class.cancelled",
            entity_type="class",
            entity_id=str(item.id),
            reason=item.cancellation_reason,
            outcome="cancelled",
            summary=f"Class '{item.title}' was cancelled.",
            before_data=before,
            after_data=self._audit_data(item),
        )
        await self.session.commit()
        await self.session.refresh(item)
        return self._item(item, trainer_name)

    async def _trainer_name(self, trainer_id: UUID | None, *, require_active: bool = True) -> str | None:
        if not trainer_id:
            return None
        trainer = await self.classes.get_trainer(trainer_id)
        if not trainer or (require_active and not trainer.is_active):
            raise AppError("TRAINER_UNAVAILABLE", "The selected trainer is unavailable.", 422)
        return trainer.display_name

    async def _ensure_no_overlap(self, **values) -> None:
        conflict = await self.classes.find_overlap(**values)
        if conflict:
            raise ConflictError(
                "The trainer or location is already assigned to an overlapping class.",
                {"conflicting_class_id": str(conflict.id), "conflicting_title": conflict.title},
            )

    @staticmethod
    def _item(item: GymClass, trainer_name: str | None) -> ClassItem:
        return ClassItem(
            id=item.id,
            title=item.title,
            class_type=item.class_type,
            description=item.description,
            start_at=item.start_at,
            end_at=item.end_at,
            capacity=item.capacity,
            status=item.status,
            trainer_id=item.trainer_id,
            trainer_name=trainer_name,
            location=item.location,
            cancellation_reason=item.cancellation_reason,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def _audit_data(item: GymClass) -> dict[str, object]:
        return {
            "title": item.title,
            "class_type": item.class_type,
            "start_at": item.start_at.isoformat(),
            "end_at": item.end_at.isoformat(),
            "capacity": item.capacity,
            "trainer_id": str(item.trainer_id) if item.trainer_id else None,
            "location": item.location,
            "status": item.status,
        }
