from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.membership_schema import (
    PurchaseMembershipRequest,
    PurchaseMembershipResponse,
)
from app.schemas.operations_schema import (
    CancellationRequestCreate,
    FreezeRequestCreate,
    MembershipRequestItem,
)
from app.services.lifecycle_service import MembershipLifecycleService
from app.services.membership_service import MembershipService

router = APIRouter(prefix="/memberships", tags=["memberships"])


@router.post("/purchase", response_model=PurchaseMembershipResponse)
async def purchase_membership(
    payload: PurchaseMembershipRequest,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PurchaseMembershipResponse:
    return await MembershipService(session).purchase(
        current_user=current_user,
        payload=payload,
    )


@router.post("/freeze-requests", response_model=MembershipRequestItem)
async def request_freeze(
    payload: FreezeRequestCreate,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MembershipRequestItem:
    return await MembershipLifecycleService(session).create_freeze_request(user=current_user, payload=payload)


@router.post("/cancellation-requests", response_model=MembershipRequestItem)
async def request_cancellation(
    payload: CancellationRequestCreate,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MembershipRequestItem:
    return await MembershipLifecycleService(session).create_cancellation_request(user=current_user, payload=payload)


@router.get("/requests/me", response_model=list[MembershipRequestItem])
async def list_my_membership_requests(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[MembershipRequestItem]:
    return await MembershipLifecycleService(session).list_my_requests(current_user)
