from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.training_schema import ExerciseHistoryPage, ExerciseItem, ExercisePage, ExerciseUpdate, ExerciseWrite, Muscle, Region, WorkoutDayDetail, WorkoutExerciseWrite, WorkoutHistoryPage, WorkoutToday, WorkoutWeekSummary
from app.services.training_service import TrainingService
from app.services.workout_service import WorkoutService

router = APIRouter(prefix="/training/exercises", tags=["training catalogue"])
admin_router = APIRouter(prefix="/admin/training/exercises", tags=["training catalogue administration"])
workout_router = APIRouter(prefix="/training/workouts", tags=["member workouts"])


@router.get("", response_model=ExercisePage)
async def list_exercises(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    region: Region | None = None,
    muscle: Muscle | None = None,
    search: str | None = Query(None, max_length=160),
) -> ExercisePage:
    return await TrainingService(session).list(page=page, page_size=page_size, region=region, muscle=muscle, search=search)


@router.get("/{exercise_id}", response_model=ExerciseItem)
async def get_exercise(exercise_id: UUID, current_user: Annotated[User, Depends(require_roles("member"))], session: Annotated[AsyncSession, Depends(get_db_session)]) -> ExerciseItem:
    return await TrainingService(session).get(exercise_id)


@router.get("/{exercise_id}/history", response_model=ExerciseHistoryPage)
async def get_exercise_history(
    exercise_id: UUID,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
) -> ExerciseHistoryPage:
    return await WorkoutService(session).exercise_history(current_user, exercise_id=exercise_id, page=page, page_size=page_size)


@router.get("/{exercise_id}/image")
async def get_image(exercise_id: UUID, session: Annotated[AsyncSession, Depends(get_db_session)]) -> Response:
    return Response(await TrainingService(session).image(exercise_id), media_type="image/jpeg", headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"})


@admin_router.get("", response_model=ExercisePage)
async def admin_list_exercises(
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    region: Region | None = None,
    muscle: Muscle | None = None,
    search: str | None = Query(None, max_length=160),
) -> ExercisePage:
    return await TrainingService(session).list(page=page, page_size=page_size, region=region, muscle=muscle, search=search, include_inactive=True)


@admin_router.get("/{exercise_id}", response_model=ExerciseItem)
async def admin_get_exercise(exercise_id: UUID, current_user: Annotated[User, Depends(require_roles("manager", "admin"))], session: Annotated[AsyncSession, Depends(get_db_session)]) -> ExerciseItem:
    return await TrainingService(session).get(exercise_id, include_inactive=True)


@admin_router.post("", response_model=ExerciseItem, status_code=201)
async def create_exercise(payload: ExerciseWrite, current_user: Annotated[User, Depends(require_roles("manager", "admin"))], session: Annotated[AsyncSession, Depends(get_db_session)]) -> ExerciseItem:
    return await TrainingService(session).create(actor=current_user, payload=payload)


@admin_router.patch("/{exercise_id}", response_model=ExerciseItem)
async def update_exercise(exercise_id: UUID, payload: ExerciseUpdate, current_user: Annotated[User, Depends(require_roles("manager", "admin"))], session: Annotated[AsyncSession, Depends(get_db_session)]) -> ExerciseItem:
    return await TrainingService(session).update(exercise_id=exercise_id, actor=current_user, payload=payload)


@admin_router.put("/{exercise_id}/image", response_model=ExerciseItem)
async def set_exercise_image(exercise_id: UUID, current_user: Annotated[User, Depends(require_roles("manager", "admin"))], session: Annotated[AsyncSession, Depends(get_db_session)], file: UploadFile = File(...)) -> ExerciseItem:
    content = await file.read(2_000_001)
    return await TrainingService(session).set_image(exercise_id=exercise_id, actor=current_user, content=content)


@workout_router.get("/today", response_model=WorkoutToday)
async def get_today_workout(current_user: Annotated[User, Depends(require_roles("member"))], session: Annotated[AsyncSession, Depends(get_db_session)]) -> WorkoutToday:
    return await WorkoutService(session).today(current_user)


@workout_router.post("/today/exercises", response_model=WorkoutToday)
async def add_today_exercise(payload: WorkoutExerciseWrite, current_user: Annotated[User, Depends(require_roles("member"))], session: Annotated[AsyncSession, Depends(get_db_session)]) -> WorkoutToday:
    return await WorkoutService(session).add_exercise(current_user, payload)


@workout_router.get("/history", response_model=WorkoutHistoryPage)
async def get_workout_history(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    date_from: date,
    date_to: date,
    page: int = Query(1, ge=1),
    page_size: int = Query(31, ge=1, le=100),
) -> WorkoutHistoryPage:
    return await WorkoutService(session).history(current_user, date_from=date_from, date_to=date_to, page=page, page_size=page_size)


@workout_router.get("/muscle-map", response_model=WorkoutWeekSummary)
async def get_workout_muscle_map(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    week_of: date | None = None,
) -> WorkoutWeekSummary:
    return await WorkoutService(session).week(current_user, week_of=week_of)


@workout_router.get("/{workout_date}", response_model=WorkoutDayDetail)
async def get_workout_day(workout_date: date, current_user: Annotated[User, Depends(require_roles("member"))], session: Annotated[AsyncSession, Depends(get_db_session)]) -> WorkoutDayDetail:
    return await WorkoutService(session).day(current_user, workout_date)
