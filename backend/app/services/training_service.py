from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from math import ceil
from uuid import UUID

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ResourceNotFoundError
from app.models.training import TrainingExercise, TrainingExerciseImage
from app.models.user import User
from app.repositories.operations_repository import AuditRepository
from app.repositories.training_repository import TrainingRepository
from app.schemas.operations_schema import PageInfo
from app.schemas.training_schema import ExerciseItem, ExercisePage, ExerciseUpdate, ExerciseWrite


class TrainingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.exercises = TrainingRepository(session)
        self.audit = AuditRepository(session)

    async def list(self, *, page: int, page_size: int, region: str | None, muscle: str | None, search: str | None, include_inactive: bool = False) -> ExercisePage:
        rows, total = await self.exercises.list(page=page, page_size=page_size, region=region, muscle=muscle, search=search.strip() if search else None, include_inactive=include_inactive)
        items = await self._items(rows)
        return ExercisePage(items=items, page=PageInfo(page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0))

    async def get(self, exercise_id: UUID, *, include_inactive: bool = False) -> ExerciseItem:
        row = await self.exercises.get(exercise_id)
        if not row or (not include_inactive and not row.is_active):
            raise ResourceNotFoundError("Exercise was not found.")
        return (await self._items([row]))[0]

    async def create(self, *, actor: User, payload: ExerciseWrite) -> ExerciseItem:
        data = payload.model_dump(exclude={"primary_muscles", "secondary_muscles"})
        row = TrainingExercise(**data)
        self.session.add(row)
        await self.session.flush()
        await self.exercises.replace_muscles(row.id, payload.primary_muscles, payload.secondary_muscles)
        await self.audit.create(actor_user_id=actor.id, action="training.exercise.created", entity_type="training_exercise", entity_id=str(row.id), summary="Exercise created.", after_data=payload.model_dump())
        await self.session.commit()
        await self.session.refresh(row)
        return (await self._items([row]))[0]

    async def update(self, *, exercise_id: UUID, actor: User, payload: ExerciseUpdate) -> ExerciseItem:
        row = await self.exercises.get(exercise_id, for_update=True)
        if not row:
            raise ResourceNotFoundError("Exercise was not found.")
        before = (await self._items([row]))[0]
        changes = payload.model_dump(exclude_unset=True)
        try:
            merged = ExerciseWrite.model_validate({**before.model_dump(exclude={"id", "has_image", "created_at", "updated_at"}), **changes})
        except ValidationError as exc:
            raise AppError("EXERCISE_INVALID", "Exercise details are invalid. Check text lengths and muscle roles.", 422) from exc
        for key, value in merged.model_dump(exclude={"primary_muscles", "secondary_muscles"}).items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await self.exercises.replace_muscles(row.id, merged.primary_muscles, merged.secondary_muscles)
        await self.audit.create(actor_user_id=actor.id, action="training.exercise.updated", entity_type="training_exercise", entity_id=str(row.id), summary="Exercise updated.", before_data=before.model_dump(mode="json"), after_data=merged.model_dump())
        await self.session.commit()
        await self.session.refresh(row)
        return (await self._items([row]))[0]

    async def set_image(self, *, exercise_id: UUID, actor: User, content: bytes) -> ExerciseItem:
        row = await self.exercises.get(exercise_id, for_update=True)
        if not row:
            raise ResourceNotFoundError("Exercise was not found.")
        if len(content) > 2_000_000 or not content:
            raise AppError("IMAGE_SIZE_INVALID", "Choose an image smaller than 2 MB.", 422)
        try:
            with Image.open(BytesIO(content)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"} or source.width * source.height > 4_000_000:
                    raise ValueError("Unsupported image or dimensions.")
                image = ImageOps.exif_transpose(source).convert("RGB")
                output = BytesIO()
                image.save(output, format="JPEG", quality=82, optimize=True)
                sanitized = output.getvalue()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise AppError("IMAGE_INVALID", "Choose a valid PNG, JPEG or WebP image up to 4 megapixels.", 422) from exc
        if len(sanitized) > 4_000_000:
            raise AppError("IMAGE_SIZE_INVALID", "The processed image is too large.", 422)
        now = datetime.now(UTC)
        existing = await self.exercises.image(exercise_id)
        if existing:
            existing.image_data = sanitized
            existing.updated_at = now
        else:
            self.session.add(TrainingExerciseImage(exercise_id=exercise_id, image_data=sanitized, updated_at=now))
        row.updated_at = now
        await self.audit.create(actor_user_id=actor.id, action="training.exercise.image_updated", entity_type="training_exercise", entity_id=str(row.id), summary="Exercise image replaced." if existing else "Exercise image added.", before_data={"has_image": bool(existing)}, after_data={"has_image": True})
        await self.session.commit()
        await self.session.refresh(row)
        return (await self._items([row]))[0]

    async def image(self, exercise_id: UUID) -> bytes:
        row = await self.exercises.get(exercise_id)
        if not row or not row.is_active:
            raise ResourceNotFoundError("Exercise image was not found.")
        image = await self.exercises.image(exercise_id)
        if not image:
            raise ResourceNotFoundError("Exercise image was not found.")
        return image.image_data

    async def _items(self, rows: list[TrainingExercise]) -> list[ExerciseItem]:
        ids = [row.id for row in rows]
        muscles = await self.exercises.muscles(ids)
        images = await self.exercises.image_ids(ids)
        return [ExerciseItem.model_validate({"id": row.id, "name": row.name, "description": row.description, "region": row.region, "usage_steps": row.usage_steps, "safety_note": row.safety_note, "primary_muscles": muscles[row.id][0], "secondary_muscles": muscles[row.id][1], "is_illustrative": row.is_illustrative, "is_active": row.is_active, "has_image": row.id in images, "created_at": row.created_at, "updated_at": row.updated_at}) for row in rows]
