from __future__ import annotations

from uuid import UUID

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import TrainingExercise, TrainingExerciseImage, TrainingExerciseMuscle


class TrainingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, *, page: int, page_size: int, region: str | None, muscle: str | None, search: str | None, include_inactive: bool) -> tuple[list[TrainingExercise], int]:
        query = select(TrainingExercise)
        if not include_inactive:
            query = query.where(TrainingExercise.is_active.is_(True))
        if region:
            query = query.where(TrainingExercise.region == region)
        if muscle:
            query = query.where(exists(select(TrainingExerciseMuscle.id).where(TrainingExerciseMuscle.exercise_id == TrainingExercise.id, TrainingExerciseMuscle.muscle == muscle)))
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            term = f"%{escaped}%"
            query = query.where(or_(TrainingExercise.name.ilike(term, escape="\\"), exists(select(TrainingExerciseMuscle.id).where(TrainingExerciseMuscle.exercise_id == TrainingExercise.id, TrainingExerciseMuscle.muscle.ilike(term, escape="\\")))))
        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (await self.session.execute(query.order_by(TrainingExercise.name, TrainingExercise.id).offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return list(rows), total

    async def get(self, exercise_id: UUID, *, for_update: bool = False) -> TrainingExercise | None:
        query = select(TrainingExercise).where(TrainingExercise.id == exercise_id)
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def muscles(self, exercise_ids: list[UUID]) -> dict[UUID, tuple[list[str], list[str]]]:
        result = {item: ([], []) for item in exercise_ids}
        if exercise_ids:
            rows = (await self.session.execute(select(TrainingExerciseMuscle).where(TrainingExerciseMuscle.exercise_id.in_(exercise_ids)).order_by(TrainingExerciseMuscle.muscle))).scalars().all()
            for row in rows:
                result[row.exercise_id][0 if row.role == "primary" else 1].append(row.muscle)
        return result

    async def image_ids(self, exercise_ids: list[UUID]) -> set[UUID]:
        if not exercise_ids:
            return set()
        return set((await self.session.execute(select(TrainingExerciseImage.exercise_id).where(TrainingExerciseImage.exercise_id.in_(exercise_ids)))).scalars().all())

    async def image(self, exercise_id: UUID) -> TrainingExerciseImage | None:
        return (await self.session.execute(select(TrainingExerciseImage).where(TrainingExerciseImage.exercise_id == exercise_id))).scalar_one_or_none()

    async def replace_muscles(self, exercise_id: UUID, primary: list[str], secondary: list[str]) -> None:
        rows = (await self.session.execute(select(TrainingExerciseMuscle).where(TrainingExerciseMuscle.exercise_id == exercise_id))).scalars().all()
        for row in rows:
            await self.session.delete(row)
        await self.session.flush()
        self.session.add_all([TrainingExerciseMuscle(exercise_id=exercise_id, muscle=muscle, role=role) for role, muscles in (("primary", primary), ("secondary", secondary)) for muscle in muscles])
