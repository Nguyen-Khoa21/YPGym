from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.membership_schema import MembershipPlanResponse
from app.services.membership_plan_service import MembershipPlanService

router = APIRouter(prefix="/membership-plans", tags=["membership plans"])


@router.get("", response_model=list[MembershipPlanResponse])
async def list_membership_plans(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[MembershipPlanResponse]:
    return await MembershipPlanService(session).list_active_plans()
