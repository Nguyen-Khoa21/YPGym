from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, oauth2_scheme
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth_schema import LoginResponse
from app.schemas.identity_schema import IdentityListResponse, OAuthExchangeRequest, OAuthStartResponse, ProviderStatus
from app.services.oauth_service import OAuthService

Provider = Literal["google", "facebook"]
Platform = Literal["web", "mobile"]

auth_router = APIRouter(prefix="/auth", tags=["auth providers"])
account_router = APIRouter(prefix="/account", tags=["account security"])


@auth_router.get("/providers", response_model=list[ProviderStatus])
async def providers(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> list[ProviderStatus]:
    return OAuthService(session, redis).providers()


@auth_router.get("/oauth/{provider}/start", response_model=OAuthStartResponse)
async def oauth_start(
    provider: Provider,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    platform: Platform = Query("web"),
) -> OAuthStartResponse:
    return await OAuthService(session, redis).start(provider=provider, platform=platform)


@auth_router.get("/oauth/{provider}/callback", response_class=RedirectResponse)
async def oauth_callback(
    provider: Provider,
    state: Annotated[str, Query(min_length=16, max_length=512)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    code: str | None = Query(None, max_length=4096),
    error: str | None = Query(None, max_length=128),
) -> RedirectResponse:
    target = await OAuthService(session, redis).callback(provider=provider, state=state, code=code, error=error)
    return RedirectResponse(target, status_code=302)


@auth_router.post("/oauth/{provider}/exchange", response_model=LoginResponse)
async def oauth_web_exchange(
    provider: Provider,
    payload: OAuthExchangeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> LoginResponse:
    return await OAuthService(session, redis).exchange(provider=provider, platform="web", code=payload.code)


@auth_router.post("/oauth/{provider}/mobile/exchange", response_model=LoginResponse)
async def oauth_mobile_exchange(
    provider: Provider,
    payload: OAuthExchangeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> LoginResponse:
    return await OAuthService(session, redis).exchange(provider=provider, platform="mobile", code=payload.code)


@account_router.get("/identities", response_model=IdentityListResponse)
async def list_identities(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> IdentityListResponse:
    return await OAuthService(session, redis).list_identities(current_user)


@account_router.post("/identities/{provider}/link/start", response_model=OAuthStartResponse)
async def link_identity_start(
    provider: Provider,
    current_user: Annotated[User, Depends(get_current_user)],
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    platform: Platform = Query("web"),
) -> OAuthStartResponse:
    service = OAuthService(session, redis)
    service.require_recent_auth(token)
    return await service.start(provider=provider, platform=platform, purpose="link", user_id=current_user.id)


@account_router.delete("/identities/{provider}", response_model=IdentityListResponse)
async def unlink_identity(
    provider: Provider,
    current_user: Annotated[User, Depends(get_current_user)],
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> IdentityListResponse:
    service = OAuthService(session, redis)
    service.require_recent_auth(token)
    return await service.unlink(user=current_user, provider=provider)
