from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.class_schema import ClassCancel, ClassCreate, ClassItem, ClassPage, ClassUpdate, TrainerItem
from app.services.class_service import ClassService

router = APIRouter(prefix="/admin/classes", tags=["class administration"])


@router.get("", response_model=ClassPage)
async def list_classes(
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status: Literal["scheduled", "cancelled", "completed"] | None = None,
    trainer_id: UUID | None = None,
    search: str | None = Query(None, max_length=160),
) -> ClassPage:
    return await ClassService(session).list_classes(
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        status=status,
        trainer_id=trainer_id,
        search=search,
    )


@router.get("/trainers", response_model=list[TrainerItem])
async def list_trainers(
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[TrainerItem]:
    return await ClassService(session).list_trainers()


@router.post("", response_model=ClassItem)
async def create_class(
    payload: ClassCreate,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassItem:
    return await ClassService(session).create(actor=current_user, payload=payload)


@router.patch("/{class_id}", response_model=ClassItem)
async def update_class(
    class_id: UUID,
    payload: ClassUpdate,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassItem:
    return await ClassService(session).update(class_id=class_id, actor=current_user, payload=payload)


@router.post("/{class_id}/cancel", response_model=ClassItem)
async def cancel_class(
    class_id: UUID,
    payload: ClassCancel,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassItem:
    return await ClassService(session).cancel(class_id=class_id, actor=current_user, payload=payload)
