from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.class_schema import (
    ClassCancel,
    ClassCreate,
    ClassItem,
    ClassPage,
    ClassUpdate,
    BookingItem,
    MemberClassItem,
    MemberClassList,
    MemberBookings,
    TrainerAdminItem,
    TrainerCreate,
    TrainerItem,
    TrainerUpdate,
    WaitlistItem,
)
from app.services.class_service import BookingService, ClassService, TrainerService

router = APIRouter(prefix="/admin/classes", tags=["class administration"])
trainer_router = APIRouter(prefix="/trainers", tags=["trainers"])
admin_trainer_router = APIRouter(prefix="/admin/trainers", tags=["trainer administration"])
member_class_router = APIRouter(prefix="/classes", tags=["member classes"])
booking_router = APIRouter(prefix="/bookings", tags=["member bookings"])


@member_class_router.get("/upcoming", response_model=MemberClassList)
async def upcoming_classes(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> MemberClassList:
    return await BookingService(session, redis).list_upcoming(current_user)


@member_class_router.get("/{class_id}", response_model=MemberClassItem)
async def member_class(
    class_id: UUID,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> MemberClassItem:
    return await BookingService(session, redis).get_member_class(class_id=class_id, user=current_user)


@member_class_router.post("/{class_id}/book", response_model=BookingItem)
async def book_class(
    class_id: UUID,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> BookingItem:
    return await BookingService(session, redis).book(class_id=class_id, user=current_user)


@member_class_router.post("/{class_id}/waitlist", response_model=WaitlistItem)
async def join_waitlist(
    class_id: UUID,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> WaitlistItem:
    return await BookingService(session, redis).join_waitlist(class_id=class_id, user=current_user)


@member_class_router.delete("/{class_id}/waitlist", response_model=WaitlistItem)
async def leave_waitlist(
    class_id: UUID,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> WaitlistItem:
    return await BookingService(session, redis).leave_waitlist(class_id=class_id, user=current_user)


@booking_router.get("/me", response_model=MemberBookings)
async def my_bookings(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> MemberBookings:
    return await BookingService(session, redis).list_my(current_user)


@booking_router.post("/{booking_id}/cancel", response_model=BookingItem)
async def cancel_booking(
    booking_id: UUID,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> BookingItem:
    return await BookingService(session, redis).cancel(booking_id=booking_id, user=current_user)


@trainer_router.get("", response_model=list[TrainerItem])
async def public_trainers(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[TrainerItem]:
    return await TrainerService(session).list_public()


@trainer_router.get("/{trainer_id}", response_model=TrainerItem)
async def public_trainer(
    trainer_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TrainerItem:
    return await TrainerService(session).get_public(trainer_id)


@admin_trainer_router.get("", response_model=list[TrainerAdminItem])
async def admin_trainers(
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    active: bool | None = None,
) -> list[TrainerAdminItem]:
    return await TrainerService(session).list_admin(active=active)


@admin_trainer_router.post("", response_model=TrainerAdminItem)
async def create_trainer(
    payload: TrainerCreate,
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TrainerAdminItem:
    return await TrainerService(session).create(actor=current_user, payload=payload)


@admin_trainer_router.patch("/{trainer_id}", response_model=TrainerAdminItem)
async def update_trainer(
    trainer_id: UUID,
    payload: TrainerUpdate,
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TrainerAdminItem:
    return await TrainerService(session).update(trainer_id=trainer_id, actor=current_user, payload=payload)


@admin_trainer_router.post("/{trainer_id}/deactivate", response_model=TrainerAdminItem)
async def deactivate_trainer(
    trainer_id: UUID,
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TrainerAdminItem:
    return await TrainerService(session).deactivate(trainer_id=trainer_id, actor=current_user)


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
