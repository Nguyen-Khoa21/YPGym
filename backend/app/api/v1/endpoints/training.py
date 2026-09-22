from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.training_schema import ExerciseItem, ExercisePage, ExerciseUpdate, ExerciseWrite, Muscle, Region
from app.services.training_service import TrainingService

router = APIRouter(prefix="/training/exercises", tags=["training catalogue"])
admin_router = APIRouter(prefix="/admin/training/exercises", tags=["training catalogue administration"])


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
