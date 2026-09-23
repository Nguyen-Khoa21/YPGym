from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, ResourceNotFoundError
from app.models.training import WorkoutExercise, WorkoutSession, WorkoutSet
from app.models.user import User
from app.repositories.operations_repository import AuditRepository
from app.repositories.training_repository import TrainingRepository
from app.schemas.training_schema import WorkoutExerciseItem, WorkoutExerciseWrite, WorkoutSessionItem, WorkoutSetItem, WorkoutToday
from app.services.lifecycle_service import MembershipLifecycleService


class WorkoutService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = TrainingRepository(session)
        self.timezone = ZoneInfo(get_settings().GYM_TIMEZONE)

    def _today_window(self, now: datetime) -> tuple[date, datetime, datetime]:
        day = now.astimezone(self.timezone).date()
        start = datetime.combine(day, time.min, self.timezone).astimezone(UTC)
        end = datetime.combine(day + timedelta(days=1), time.min, self.timezone).astimezone(UTC)
        return day, start, end

    async def today(self, user: User) -> WorkoutToday:
        day, start, end = self._today_window(datetime.now(UTC))
        attendance = await self.repository.qualifying_check_in(user.id, start, end)
        workout = await self.repository.workout(user.id, day)
        _, _, membership_eligible, _ = await MembershipLifecycleService(self.session).access_snapshot(user)
        eligible = attendance is not None and membership_eligible
        return WorkoutToday(
            gym_date=day,
            gym_timezone=self.timezone.key,
            eligible=eligible,
            reason=None if eligible else "Scan your QR code at the gym today before logging exercises." if not attendance else "An active membership is required to add exercises.",
            session=await self._item(workout) if workout else None,
        )

    async def add_exercise(self, user: User, payload: WorkoutExerciseWrite) -> WorkoutToday:
        # Serialize all writes for this member; the unique day and request-key constraints remain the database backstop.
        await self.session.execute(select(User.id).where(User.id == user.id).with_for_update())
        now = datetime.now(UTC)
        day, start, end = self._today_window(now)
        attendance = await self.repository.qualifying_check_in(user.id, start, end)
        if not attendance:
            raise AppError("WORKOUT_CHECK_IN_REQUIRED", "Scan your QR code at the gym today before logging exercises.", 403)
        await MembershipLifecycleService(self.session).require_eligible_membership(user)
        workout = await self.repository.workout(user.id, day)
        if workout:
            rows = await self.repository.workout_exercises(workout.id)
            existing = next((row for row in rows if row.idempotency_key == payload.idempotency_key), None)
            if existing:
                sets = await self.repository.workout_sets([existing.id])
                if existing.exercise_id != payload.exercise_id or [(row.reps, row.weight, row.unit) for row in sets] != [(row.reps, row.weight, row.unit) for row in payload.sets]:
                    raise AppError("WORKOUT_REQUEST_CONFLICT", "This submission key was already used for different exercise details.", 409)
                return await self.today(user)
        exercise = await self.repository.get(payload.exercise_id)
        if not exercise or not exercise.is_active:
            raise ResourceNotFoundError("Active exercise was not found.")
        if not workout:
            workout = WorkoutSession(user_id=user.id, attendance_session_id=attendance.id, workout_date=day)
            self.session.add(workout)
            await self.session.flush()
        muscles = (await self.repository.muscles([exercise.id]))[exercise.id]
        row = WorkoutExercise(
            session_id=workout.id,
            exercise_id=exercise.id,
            idempotency_key=payload.idempotency_key,
            name_snapshot=exercise.name,
            primary_muscles_snapshot=muscles[0],
            secondary_muscles_snapshot=muscles[1],
            created_at=now,
        )
        self.session.add(row)
        await self.session.flush()
        self.session.add_all([
            WorkoutSet(workout_exercise_id=row.id, set_order=index, reps=item.reps, weight=item.weight, unit=item.unit)
            for index, item in enumerate(payload.sets, start=1)
        ])
        workout.updated_at = now
        await AuditRepository(self.session).create(
            actor_user_id=user.id,
            target_user_id=user.id,
            action="training.workout_exercise.created",
            entity_type="workout_exercise",
            entity_id=str(row.id),
            summary="Member logged an exercise in today's attendance-linked workout.",
        )
        await self.session.commit()
        return await self.today(user)

    async def _item(self, workout: WorkoutSession) -> WorkoutSessionItem:
        rows = await self.repository.workout_exercises(workout.id)
        sets = await self.repository.workout_sets([row.id for row in rows])
        grouped: dict[UUID, list[WorkoutSetItem]] = {row.id: [] for row in rows}
        for item in sets:
            grouped[item.workout_exercise_id].append(WorkoutSetItem(id=item.id, set_order=item.set_order, reps=item.reps, weight=item.weight, unit=item.unit))
        return WorkoutSessionItem(
            id=workout.id,
            workout_date=workout.workout_date,
            attendance_session_id=workout.attendance_session_id,
            exercises=[WorkoutExerciseItem(id=row.id, exercise_id=row.exercise_id, name=row.name_snapshot, primary_muscles=row.primary_muscles_snapshot, secondary_muscles=row.secondary_muscles_snapshot, created_at=row.created_at, sets=grouped[row.id]) for row in rows],
        )
