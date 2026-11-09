from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.core.rate_limit import rate_limits
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.membership_schema import PurchaseMembershipResponse
from app.schemas.payment_schema import PayOSCreateResponse
from app.schemas.staff_schema import (
    InPersonMemberRegister,
    InPersonMemberRegistered,
    StaffMembershipPaymentRequest,
    StaffPaymentStatus,
    MyStaffShifts,
    StaffAccountCreate,
    StaffAccountCreated,
    StaffAccountPage,
    StaffShiftItem,
    StaffShiftPage,
)
from app.services.in_person_service import InPersonMemberService
from app.services.staff_service import StaffOperationsService
from app.utils.security import hash_token

router = APIRouter(prefix="/staff", tags=["staff time clock"])
admin_router = APIRouter(prefix="/admin", tags=["staff administration"])


@router.get("/shifts/me", response_model=MyStaffShifts)
async def my_shifts(
    current_user: Annotated[User, Depends(require_roles("staff", "pt"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MyStaffShifts:
    return await StaffOperationsService(session).my_shifts(user=current_user)


@router.post("/shifts/clock-in", response_model=StaffShiftItem, status_code=201)
async def clock_in(
    current_user: Annotated[User, Depends(require_roles("staff", "pt"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StaffShiftItem:
    return await StaffOperationsService(session).clock_in(user=current_user)


@router.post("/shifts/clock-out", response_model=StaffShiftItem)
async def clock_out(
    current_user: Annotated[User, Depends(require_roles("staff", "pt"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StaffShiftItem:
    return await StaffOperationsService(session).clock_out(user=current_user)


async def _limit_in_person(redis: Redis, actor: User, action: str, limit: int) -> None:
    await rate_limits.enforce(
        redis,
        key=f"ypgym:rate:in-person-{action}:{hash_token(str(actor.id))}",
        limit=limit,
        window_seconds=3600,
    )


@router.post("/members", response_model=InPersonMemberRegistered, status_code=201)
async def register_in_person_member(
    payload: InPersonMemberRegister,
    response: Response,
    current_user: Annotated[User, Depends(require_roles("staff", "manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> InPersonMemberRegistered:
    await _limit_in_person(redis, current_user, "register", 30)
    response.headers["Cache-Control"] = "no-store"
    return await InPersonMemberService(session).register(actor=current_user, payload=payload)


@router.post("/members/{user_id}/membership-checkout", response_model=PayOSCreateResponse, status_code=201)
async def create_member_qr_checkout(
    user_id: UUID,
    payload: StaffMembershipPaymentRequest,
    response: Response,
    current_user: Annotated[User, Depends(require_roles("staff", "manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> PayOSCreateResponse:
    await _limit_in_person(redis, current_user, "checkout", 60)
    response.headers["Cache-Control"] = "no-store"
    return await InPersonMemberService(session).create_qr_checkout(actor=current_user, user_id=user_id, payload=payload)


@router.post("/members/{user_id}/membership-cash", response_model=PurchaseMembershipResponse)
async def record_member_cash_payment(
    user_id: UUID,
    payload: StaffMembershipPaymentRequest,
    current_user: Annotated[User, Depends(require_roles("staff", "manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> PurchaseMembershipResponse:
    await _limit_in_person(redis, current_user, "cash", 60)
    return await InPersonMemberService(session).record_cash(actor=current_user, user_id=user_id, payload=payload)


@router.get("/payments/{payment_id}", response_model=StaffPaymentStatus)
async def staff_payment_status(
    payment_id: UUID,
    response: Response,
    current_user: Annotated[User, Depends(require_roles("staff", "manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StaffPaymentStatus:
    response.headers["Cache-Control"] = "no-store"
    return await InPersonMemberService(session).payment_status(actor=current_user, payment_id=payment_id)


@admin_router.get("/staff-accounts", response_model=StaffAccountPage)
async def list_staff_accounts(
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=160),
    role: Literal["staff", "pt"] | None = None,
    gym_id: UUID | None = None,
) -> StaffAccountPage:
    return await StaffOperationsService(session).list_accounts(
        actor=current_user,
        gym_id=gym_id,
        page=page,
        page_size=page_size,
        search=search,
        role=role,
    )


@admin_router.post("/staff-accounts", response_model=StaffAccountCreated, status_code=201)
async def create_staff_account(
    payload: StaffAccountCreate,
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StaffAccountCreated:
    return await StaffOperationsService(session).create_account(actor=current_user, payload=payload)


@admin_router.get("/staff-shifts", response_model=StaffShiftPage)
async def list_staff_shifts(
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=160),
    role: Literal["staff", "pt"] | None = None,
    status: Literal["open", "closed"] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    gym_id: UUID | None = None,
) -> StaffShiftPage:
    return await StaffOperationsService(session).list_shifts(
        actor=current_user,
        gym_id=gym_id,
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
