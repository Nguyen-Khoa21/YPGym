from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from redis.asyncio import Redis

from app.core.dependencies import get_current_user, require_roles
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth_schema import UserPublic
from app.schemas.onboarding_schema import OnboardingAnswers, OnboardingResponse, RecommendationsResponse
from app.schemas.user_schema import UserProfileUpdateRequest
from app.services.onboarding_service import OnboardingService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.patch("/me", response_model=UserPublic)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserPublic:
    return await UserService(session).update_profile(
        current_user=current_user,
        payload=payload,
    )


@router.get("/me/onboarding", response_model=OnboardingResponse)
async def get_my_onboarding(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OnboardingResponse:
    return await OnboardingService(session).get(user=current_user)


@router.put("/me/onboarding", response_model=OnboardingResponse)
async def save_my_onboarding(
    payload: OnboardingAnswers,
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OnboardingResponse:
    return await OnboardingService(session).save(user=current_user, payload=payload)


@router.post("/me/onboarding/skip", response_model=OnboardingResponse)
async def skip_my_onboarding(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OnboardingResponse:
    return await OnboardingService(session).skip(user=current_user)


@router.get("/me/recommendations", response_model=RecommendationsResponse, response_model_exclude_none=True)
async def get_my_recommendations(
    current_user: Annotated[User, Depends(require_roles("member"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> RecommendationsResponse:
    return await OnboardingService(session, redis).recommendations(user=current_user)
