from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.gym_schema import (
    GymLocationCreate,
    GymLocationItem,
    GymLocationUpdate,
    WorkforceAssignmentCreate,
    WorkforceAssignmentItem,
)
from app.services.gym_service import GymLocationService


router = APIRouter(prefix="/gyms", tags=["gym locations"])
admin_router = APIRouter(prefix="/admin/gym-locations", tags=["gym location administration"])


@router.get("", response_model=list[GymLocationItem])
async def list_active_gyms(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[GymLocationItem]:
    return await GymLocationService(session).list_active()


@router.get("/{gym_id}", response_model=GymLocationItem)
async def get_active_gym(
    gym_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GymLocationItem:
    return await GymLocationService(session).get_active(gym_id)


@admin_router.get("", response_model=list[GymLocationItem])
async def list_gym_locations(
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[GymLocationItem]:
    return await GymLocationService(session).list_admin()


@admin_router.post("", response_model=GymLocationItem, status_code=201)
async def create_gym_location(
    payload: GymLocationCreate,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GymLocationItem:
    return await GymLocationService(session).create(actor=current_user, payload=payload)


@admin_router.patch("/{gym_id}", response_model=GymLocationItem)
async def update_gym_location(
    gym_id: UUID,
    payload: GymLocationUpdate,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GymLocationItem:
    return await GymLocationService(session).update(gym_id=gym_id, actor=current_user, payload=payload)


@admin_router.get("/workforce/assignments", response_model=list[WorkforceAssignmentItem])
async def list_workforce_assignments(
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    gym_id: UUID | None = None,
) -> list[WorkforceAssignmentItem]:
    return await GymLocationService(session).list_assignments(gym_id=gym_id)


@admin_router.put("/workforce/assignments", response_model=WorkforceAssignmentItem)
async def assign_workforce(
    payload: WorkforceAssignmentCreate,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkforceAssignmentItem:
    return await GymLocationService(session).assign_workforce(actor=current_user, payload=payload)
