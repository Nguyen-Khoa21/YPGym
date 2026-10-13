from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.staff_schema import (
    MyStaffShifts,
    StaffAccountCreate,
    StaffAccountCreated,
    StaffAccountPage,
    StaffShiftItem,
    StaffShiftPage,
)
from app.services.staff_service import StaffOperationsService

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


@admin_router.get("/staff-accounts", response_model=StaffAccountPage)
async def list_staff_accounts(
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=160),
    role: Literal["staff", "pt"] | None = None,
) -> StaffAccountPage:
    return await StaffOperationsService(session).list_accounts(
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
) -> StaffShiftPage:
    return await StaffOperationsService(session).list_shifts(
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
