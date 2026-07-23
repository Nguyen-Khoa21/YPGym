from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.dashboard_schema import MemberDashboard
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["member dashboard"])


@router.get("/me", response_model=MemberDashboard)
async def member_dashboard(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> MemberDashboard:
    return await DashboardService(session, redis).get(current_user)
