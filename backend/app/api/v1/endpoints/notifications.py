from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.notification_schema import (
    BroadcastItem,
    NotificationPage,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from app.schemas.operations_schema import OperationMessage
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/preferences/me", response_model=NotificationPreferenceResponse)
async def get_preferences(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationPreferenceResponse:
    return await NotificationService(session).get_preferences(current_user)


@router.patch("/preferences/me", response_model=NotificationPreferenceResponse)
async def update_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationPreferenceResponse:
    return await NotificationService(session).update_preferences(user=current_user, payload=payload)


@router.get("/me", response_model=NotificationPage)
async def list_notifications(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> NotificationPage:
    return await NotificationService(session).list_notifications(user=current_user, page=page, page_size=page_size)


@router.post("/me/{notification_id}/read", response_model=OperationMessage)
async def mark_read(
    notification_id: UUID,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OperationMessage:
    return await NotificationService(session).mark_read(user=current_user, notification_id=notification_id)


@router.post("/me/read-all", response_model=OperationMessage)
async def mark_all_read(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OperationMessage:
    return await NotificationService(session).mark_all_read(user=current_user)


@router.get("/broadcasts/active", response_model=list[BroadcastItem])
async def active_broadcasts(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[BroadcastItem]:
    return await NotificationService(session).list_active_broadcasts(current_user)
