from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import AwareDatetime
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.core.exceptions import AppError
from app.core.rate_limit import rate_limits
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.attendance_schema import (
    AttendancePage,
    AttendanceSessionItem,
    CrowdednessResponse,
    ManualCloseRequest,
    PeakHoursResponse,
    QrTokenResponse,
    ScannerRequest,
    ScannerResponse,
)
from app.schemas.analytics_schema import AnalyticsSummaryResponse
from app.services.analytics_service import AnalyticsService
from app.services.attendance_service import AttendanceService, CrowdednessService, QrTokenService
from app.utils.security import hash_token

router = APIRouter(prefix="/attendance", tags=["attendance"])
analytics_router = APIRouter(prefix="/admin/analytics", tags=["attendance analytics"])


@router.get("/qr-token/me", response_model=QrTokenResponse)
async def qr_token(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> QrTokenResponse:
    return await QrTokenService(session, redis).generate(current_user)


@router.post("/check-in", response_model=ScannerResponse)
async def check_in(
    payload: ScannerRequest,
    request: Request,
    device_api_key: Annotated[str, Header(alias="X-Device-Api-Key")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> ScannerResponse:
    await rate_limits.enforce(
        redis,
        key=f"ypgym:rate:scanner:ip:{hash_token(request.client.host if request.client else 'unknown')}",
        limit=120,
        window_seconds=60,
    )
    return await AttendanceService(session, redis).check_in(
        device_id=payload.device_id,
        api_key=device_api_key,
        qr_token=payload.qr_token,
    )


@router.post("/check-out", response_model=ScannerResponse)
async def check_out(
    payload: ScannerRequest,
    request: Request,
    device_api_key: Annotated[str, Header(alias="X-Device-Api-Key")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> ScannerResponse:
    await rate_limits.enforce(
        redis,
        key=f"ypgym:rate:scanner:ip:{hash_token(request.client.host if request.client else 'unknown')}",
        limit=120,
        window_seconds=60,
    )
    return await AttendanceService(session, redis).check_out(
        device_id=payload.device_id,
        api_key=device_api_key,
        qr_token=payload.qr_token,
    )


@router.get("/crowdedness", response_model=CrowdednessResponse)
async def crowdedness(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> CrowdednessResponse:
    return await CrowdednessService(session, redis).get()


@router.get("/me", response_model=AttendancePage)
async def my_attendance(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> AttendancePage:
    return await AttendanceService(session, redis).member_history(
        user=current_user,
        page=page,
        page_size=page_size,
    )


@router.get("/admin", response_model=AttendancePage)
async def admin_attendance(
    current_user: Annotated[User, Depends(require_roles("staff", "manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status: Literal["active", "checked_out", "timed_out", "manual_closed"] | None = None,
    member: str | None = Query(None, max_length=160),
) -> AttendancePage:
    return await AttendanceService(session, redis).admin_history(
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        status=status,
        member=member,
    )


@router.post("/admin/{session_id}/manual-close", response_model=AttendanceSessionItem)
async def manual_close(
    session_id: UUID,
    payload: ManualCloseRequest,
    current_user: Annotated[User, Depends(require_roles("staff", "manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> AttendanceSessionItem:
    return await AttendanceService(session, redis).manual_close(
        session_id=session_id,
        actor=current_user,
        reason=payload.reason,
    )


@analytics_router.get("/peak-hours", response_model=PeakHoursResponse)
async def peak_hours(
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    date_from: AwareDatetime | None = None,
    date_to: AwareDatetime | None = None,
) -> PeakHoursResponse:
    end = date_to or datetime.now(UTC)
    start = date_from or end - timedelta(days=30)
    if end <= start:
        raise AppError("ANALYTICS_RANGE_INVALID", "The analytics end time must be after the start time.", 422)
    if end - start > timedelta(days=366):
        raise AppError("ANALYTICS_RANGE_TOO_LARGE", "Peak-hours analytics are limited to 366 days.", 422)
    return await AttendanceService(session, redis).peak_hours(date_from=start, date_to=end)


@analytics_router.get("/summary", response_model=AnalyticsSummaryResponse)
async def analytics_summary(
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    date_from: AwareDatetime | None = None,
    date_to: AwareDatetime | None = None,
) -> AnalyticsSummaryResponse:
    end = date_to or datetime.now(UTC).replace(second=0, microsecond=0)
    start = date_from or end - timedelta(days=30)
    if end <= start:
        raise AppError("ANALYTICS_RANGE_INVALID", "The analytics end time must be after the start time.", 422)
    if end - start > timedelta(days=366):
        raise AppError("ANALYTICS_RANGE_TOO_LARGE", "Analytics summaries are limited to 366 days.", 422)
    return await AnalyticsService(session, redis).summary(date_from=start, date_to=end)
