from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from math import ceil
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
from app.schemas.operations_schema import PageInfo
from app.schemas.training_schema import (
    ExerciseHistoryItem,
    ExerciseHistoryPage,
    ExposureMetric,
    MuscleExposure,
    WorkoutComparison,
    WorkoutDayDetail,
    WorkoutExerciseItem,
    WorkoutExerciseWrite,
    WorkoutHistoryDay,
    WorkoutHistoryPage,
    WorkoutSessionItem,
    WorkoutSetItem,
    WorkoutToday,
    WorkoutWeekSummary,
)
from app.services.lifecycle_service import MembershipLifecycleService

MUSCLES = ("chest", "back", "shoulders", "biceps", "triceps", "forearms", "core", "quadriceps", "hamstrings", "glutes", "calves")
PRIMARY_EXPOSURE = Decimal("1.0")
SECONDARY_EXPOSURE = Decimal("0.5")
ZERO = Decimal("0.0")


@dataclass
class _WorkoutStats:
    item: WorkoutSessionItem
    set_count: int
    exposure_score: Decimal
    muscle_exposure: dict[str, Decimal]


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

    async def history(self, user: User, *, date_from: date, date_to: date, page: int, page_size: int) -> WorkoutHistoryPage:
        self._validate_range(date_from, date_to)
        workouts = await self.repository.workouts_between(user.id, date_from, date_to)
        attendance_days = set(await self.repository.attendance_days_between(user.id, date_from, date_to, self.timezone.key))
        stats = await self._stats(workouts)
        workout_by_day = {row.workout_date: row for row in workouts}
        scores = [stats[row.id].exposure_score for row in workouts]
        maximum = max(scores, default=ZERO)
        activity_days = sorted(attendance_days | set(workout_by_day), reverse=True)
        total = len(activity_days)
        selected_days = activity_days[(page - 1) * page_size:page * page_size]
        return WorkoutHistoryPage(
            gym_timezone=self.timezone.key,
            date_from=date_from,
            date_to=date_to,
            metric=ExposureMetric(),
            max_exposure_score=maximum,
            items=[self._history_day(day, attendance_days, workout_by_day, stats, maximum) for day in selected_days],
            page=PageInfo(page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0),
        )

    async def day(self, user: User, workout_date: date) -> WorkoutDayDetail:
        attendance_days = set(await self.repository.attendance_days_between(user.id, workout_date, workout_date, self.timezone.key))
        workout = await self.repository.workout(user.id, workout_date)
        if not workout and not attendance_days:
            raise ResourceNotFoundError("No attendance or workout activity was found for this date.")
        stats = await self._stats([workout] if workout else [])
        score = stats[workout.id].exposure_score if workout else ZERO
        return WorkoutDayDetail(
            gym_timezone=self.timezone.key,
            workout_date=workout_date,
            attended=workout_date in attendance_days,
            exposure_score=score,
            metric=ExposureMetric(),
            session=stats[workout.id].item if workout else None,
        )

    async def week(self, user: User, week_of: date | None = None) -> WorkoutWeekSummary:
        local_day = datetime.now(UTC).astimezone(self.timezone).date() if week_of is None else week_of
        week_start = local_day - timedelta(days=local_day.weekday())
        week_end = week_start + timedelta(days=6)
        workouts = await self.repository.workouts_between(user.id, week_start, week_end)
        attendance_days = set(await self.repository.attendance_days_between(user.id, week_start, week_end, self.timezone.key))
        stats = await self._stats(workouts)
        workout_by_day = {row.workout_date: row for row in workouts}
        day_maximum = max((stats[row.id].exposure_score for row in workouts), default=ZERO)
        muscle_scores = {muscle: ZERO for muscle in MUSCLES}
        for row in workouts:
            for muscle, score in stats[row.id].muscle_exposure.items():
                muscle_scores[muscle] += score
        muscle_maximum = max(muscle_scores.values(), default=ZERO)
        return WorkoutWeekSummary(
            gym_timezone=self.timezone.key,
            week_start=week_start,
            week_end=week_end,
            metric=ExposureMetric(),
            total_exposure_score=sum(muscle_scores.values(), ZERO),
            max_muscle_exposure_score=muscle_maximum,
            days=[self._history_day(week_start + timedelta(days=offset), attendance_days, workout_by_day, stats, day_maximum) for offset in range(7)],
            muscles=[MuscleExposure(muscle=muscle, exposure_score=muscle_scores[muscle], intensity_level=self._intensity(muscle_scores[muscle], muscle_maximum)) for muscle in MUSCLES],
        )

    async def exercise_history(self, user: User, *, exercise_id: UUID, page: int, page_size: int) -> ExerciseHistoryPage:
        rows, total = await self.repository.exercise_history(user_id=user.id, exercise_id=exercise_id, page=page, page_size=page_size)
        sets = await self.repository.workout_sets([row.id for row, _ in rows])
        grouped: dict[UUID, list[WorkoutSet]] = {row.id: [] for row, _ in rows}
        for item in sets:
            grouped[item.workout_exercise_id].append(item)
        summaries = [self._exercise_summary(row, workout.workout_date, grouped[row.id]) for row, workout in rows]
        items: list[ExerciseHistoryItem] = []
        for index, summary in enumerate(summaries[:page_size]):
            previous = summaries[index + 1] if index + 1 < len(summaries) else None
            items.append(ExerciseHistoryItem(
                **summary,
                comparison_to_previous=WorkoutComparison(
                    sets=self._direction(summary["set_count"], previous["set_count"]),
                    reps=self._direction(summary["total_reps"], previous["total_reps"]),
                    external_load=self._direction(summary["max_external_load_kg"], previous["max_external_load_kg"]),
                ) if previous else None,
            ))
        return ExerciseHistoryPage(
            gym_timezone=self.timezone.key,
            items=items,
            page=PageInfo(page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0),
        )

    async def _item(self, workout: WorkoutSession) -> WorkoutSessionItem:
        return (await self._stats([workout]))[workout.id].item

    async def _stats(self, workouts: list[WorkoutSession]) -> dict[UUID, _WorkoutStats]:
        rows = await self.repository.workout_exercises_for_sessions([workout.id for workout in workouts])
        sets = await self.repository.workout_sets([row.id for row in rows])
        exercises_by_session: dict[UUID, list[WorkoutExercise]] = {workout.id: [] for workout in workouts}
        sets_by_exercise: dict[UUID, list[WorkoutSet]] = {row.id: [] for row in rows}
        for row in rows:
            exercises_by_session[row.session_id].append(row)
        for item in sets:
            sets_by_exercise[item.workout_exercise_id].append(item)
        result: dict[UUID, _WorkoutStats] = {}
        for workout in workouts:
            muscle_exposure: dict[str, Decimal] = {}
            exercise_items: list[WorkoutExerciseItem] = []
            set_count = 0
            for row in exercises_by_session[workout.id]:
                row_sets = sets_by_exercise[row.id]
                set_count += len(row_sets)
                for muscle in row.primary_muscles_snapshot:
                    muscle_exposure[muscle] = muscle_exposure.get(muscle, ZERO) + PRIMARY_EXPOSURE * len(row_sets)
                for muscle in row.secondary_muscles_snapshot:
                    muscle_exposure[muscle] = muscle_exposure.get(muscle, ZERO) + SECONDARY_EXPOSURE * len(row_sets)
                exercise_items.append(WorkoutExerciseItem(
                    id=row.id,
                    exercise_id=row.exercise_id,
                    name=row.name_snapshot,
                    primary_muscles=row.primary_muscles_snapshot,
                    secondary_muscles=row.secondary_muscles_snapshot,
                    created_at=row.created_at,
                    sets=[WorkoutSetItem(id=item.id, set_order=item.set_order, reps=item.reps, weight=item.weight, unit=item.unit) for item in row_sets],
                ))
            result[workout.id] = _WorkoutStats(
                item=WorkoutSessionItem(id=workout.id, workout_date=workout.workout_date, attendance_session_id=workout.attendance_session_id, exercises=exercise_items),
                set_count=set_count,
                exposure_score=sum(muscle_exposure.values(), ZERO),
                muscle_exposure=muscle_exposure,
            )
        return result

    def _history_day(self, day: date, attendance_days: set[date], workout_by_day: dict[date, WorkoutSession], stats: dict[UUID, _WorkoutStats], maximum: Decimal) -> WorkoutHistoryDay:
        workout = workout_by_day.get(day)
        item = stats.get(workout.id) if workout else None
        score = item.exposure_score if item else ZERO
        return WorkoutHistoryDay(
            workout_date=day,
            attended=day in attendance_days,
            has_workout=workout is not None,
            exercise_count=len(item.item.exercises) if item else 0,
            set_count=item.set_count if item else 0,
            exposure_score=score,
            intensity_level=self._intensity(score, maximum),
        )

    @staticmethod
    def _validate_range(date_from: date, date_to: date) -> None:
        if date_to < date_from or (date_to - date_from).days > 365:
            raise AppError("WORKOUT_DATE_RANGE_INVALID", "Choose a date range of up to 366 days with the start on or before the end.", 422)

    @staticmethod
    def _intensity(score: Decimal, maximum: Decimal) -> int:
        if score <= 0 or maximum <= 0:
            return 0
        ratio = score / maximum
        if ratio <= Decimal("0.25"):
            return 1
        if ratio <= Decimal("0.50"):
            return 2
        if ratio <= Decimal("0.75"):
            return 3
        return 4

    @staticmethod
    def _direction(current: int | Decimal, previous: int | Decimal) -> str:
        return "more" if current > previous else "less" if current < previous else "same"

    @staticmethod
    def _exercise_summary(row: WorkoutExercise, workout_date: date, sets: list[WorkoutSet]) -> dict[str, object]:
        max_kg = max((item.weight if item.unit == "kg" else item.weight * Decimal("0.45359237") for item in sets), default=ZERO).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "workout_date": workout_date,
            "workout_exercise_id": row.id,
            "name": row.name_snapshot,
            "sets": [WorkoutSetItem(id=item.id, set_order=item.set_order, reps=item.reps, weight=item.weight, unit=item.unit) for item in sets],
            "set_count": len(sets),
            "total_reps": sum(item.reps for item in sets),
            "max_external_load_kg": max_kg,
        }
