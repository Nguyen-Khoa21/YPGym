from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceEvent, AttendanceSession
from app.models.training import TrainingExercise, TrainingExerciseImage, TrainingExerciseMuscle, WorkoutExercise, WorkoutSession, WorkoutSet


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

    async def qualifying_check_in(self, user_id: UUID, start: datetime, end: datetime) -> AttendanceSession | None:
        query = (
            select(AttendanceSession)
            .join(AttendanceEvent, AttendanceEvent.session_id == AttendanceSession.id)
            .where(
                AttendanceSession.user_id == user_id,
                AttendanceSession.source == "iot_scanner",
                AttendanceEvent.user_id == user_id,
                AttendanceEvent.event_type == "check_in",
                AttendanceEvent.source == "iot_scanner",
                AttendanceSession.checked_in_at >= start,
                AttendanceSession.checked_in_at < end,
            )
            .order_by(AttendanceSession.checked_in_at.desc())
            .limit(1)
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def workout(self, user_id: UUID, workout_date: date) -> WorkoutSession | None:
        return (await self.session.execute(select(WorkoutSession).where(WorkoutSession.user_id == user_id, WorkoutSession.workout_date == workout_date))).scalar_one_or_none()

    async def workouts_between(self, user_id: UUID, date_from: date, date_to: date) -> list[WorkoutSession]:
        return list((await self.session.execute(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id, WorkoutSession.workout_date >= date_from, WorkoutSession.workout_date <= date_to)
            .order_by(WorkoutSession.workout_date.desc()),
        )).scalars().all())

    async def attendance_days_between(self, user_id: UUID, date_from: date, date_to: date, gym_timezone: str) -> list[date]:
        local_day = cast(func.timezone(gym_timezone, AttendanceSession.checked_in_at), Date)
        return list((await self.session.execute(
            select(local_day)
            .where(AttendanceSession.user_id == user_id, local_day >= date_from, local_day <= date_to)
            .distinct()
            .order_by(local_day.desc()),
        )).scalars().all())

    async def workout_exercises(self, session_id: UUID) -> list[WorkoutExercise]:
        return list((await self.session.execute(select(WorkoutExercise).where(WorkoutExercise.session_id == session_id).order_by(WorkoutExercise.created_at, WorkoutExercise.id))).scalars().all())

    async def workout_exercises_for_sessions(self, session_ids: list[UUID]) -> list[WorkoutExercise]:
        if not session_ids:
            return []
        return list((await self.session.execute(
            select(WorkoutExercise)
            .where(WorkoutExercise.session_id.in_(session_ids))
            .order_by(WorkoutExercise.created_at, WorkoutExercise.id),
        )).scalars().all())

    async def exercise_history(self, *, user_id: UUID, exercise_id: UUID, page: int, page_size: int) -> tuple[list[tuple[WorkoutExercise, WorkoutSession]], int]:
        conditions = (WorkoutSession.user_id == user_id, WorkoutExercise.exercise_id == exercise_id)
        total = int((await self.session.execute(
            select(func.count(WorkoutExercise.id)).join(WorkoutSession, WorkoutSession.id == WorkoutExercise.session_id).where(*conditions),
        )).scalar_one())
        rows = (await self.session.execute(
            select(WorkoutExercise, WorkoutSession)
            .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.session_id)
            .where(*conditions)
            .order_by(WorkoutSession.workout_date.desc(), WorkoutExercise.created_at.desc(), WorkoutExercise.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size + 1),
        )).all()
        return [(row[0], row[1]) for row in rows], total

    async def workout_sets(self, exercise_ids: list[UUID]) -> list[WorkoutSet]:
        if not exercise_ids:
            return []
        return list((await self.session.execute(select(WorkoutSet).where(WorkoutSet.workout_exercise_id.in_(exercise_ids)).order_by(WorkoutSet.set_order))).scalars().all())
