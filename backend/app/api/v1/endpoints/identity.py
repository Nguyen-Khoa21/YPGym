from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, oauth2_scheme
from app.core.rate_limit import rate_limits
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth_schema import LoginResponse
from app.schemas.identity_schema import (
    IdentityListResponse,
    OAuthExchangeRequest,
    OAuthStartResponse,
    PendingLinkEmailConfirmRequest,
    PendingLinkEmailResponse,
    PendingLinkPasswordRequest,
    PendingLinkRequest,
    PendingLinkStatus,
    ProviderStatus,
)
from app.services.oauth_service import OAuthService
from app.utils.security import hash_token

Provider = Literal["google", "facebook"]
Platform = Literal["web", "mobile", "mobile_web"]

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
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    platform: Platform = Query("web"),
) -> OAuthStartResponse:
    client = request.client.host if request.client else "unknown"
    await rate_limits.enforce(redis, key=f"ypgym:rate:oauth-start:{hash_token(client)}", limit=30, window_seconds=60)
    return await OAuthService(session, redis).start(provider=provider, platform=platform)


@auth_router.get("/oauth/{provider}/callback", response_class=RedirectResponse)
async def oauth_callback(
    provider: Provider,
    request: Request,
    state: Annotated[str, Query(min_length=16, max_length=512)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    code: str | None = Query(None, max_length=4096),
    error: str | None = Query(None, max_length=128),
) -> RedirectResponse:
    client = request.client.host if request.client else "unknown"
    await rate_limits.enforce(redis, key=f"ypgym:rate:oauth-callback:{hash_token(client)}", limit=60, window_seconds=60)
    target = await OAuthService(session, redis).callback(provider=provider, state=state, code=code, error=error)
    return RedirectResponse(target, status_code=302)


@auth_router.post("/oauth/{provider}/exchange", response_model=LoginResponse)
async def oauth_web_exchange(
    provider: Provider,
    payload: OAuthExchangeRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> LoginResponse:
    client = request.client.host if request.client else "unknown"
    await rate_limits.enforce(redis, key=f"ypgym:rate:oauth-exchange:{hash_token(client)}", limit=30, window_seconds=60)
    return await OAuthService(session, redis).exchange(provider=provider, platform="web", code=payload.code)


@auth_router.post("/oauth/{provider}/mobile/exchange", response_model=LoginResponse)
async def oauth_mobile_exchange(
    provider: Provider,
    payload: OAuthExchangeRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> LoginResponse:
    client = request.client.host if request.client else "unknown"
    await rate_limits.enforce(redis, key=f"ypgym:rate:oauth-mobile-exchange:{hash_token(client)}", limit=30, window_seconds=60)
    return await OAuthService(session, redis).exchange(provider=provider, platform="mobile", code=payload.code)


@auth_router.post("/oauth/{provider}/mobile-web/exchange", response_model=LoginResponse)
async def oauth_mobile_web_exchange(
    provider: Provider,
    payload: OAuthExchangeRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> LoginResponse:
    client = request.client.host if request.client else "unknown"
    await rate_limits.enforce(redis, key=f"ypgym:rate:oauth-mobile-web-exchange:{hash_token(client)}", limit=30, window_seconds=60)
    return await OAuthService(session, redis).exchange(provider=provider, platform="mobile_web", code=payload.code)


@auth_router.get("/oauth/link/pending", response_model=PendingLinkStatus)
async def pending_link(
    code: Annotated[str, Query(min_length=24, max_length=512)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> PendingLinkStatus:
    return PendingLinkStatus.model_validate(await OAuthService(session, redis).pending_link_status(code))


@auth_router.post("/oauth/link/password", response_model=LoginResponse)
async def pending_link_password(
    payload: PendingLinkPasswordRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> LoginResponse:
    client = request.client.host if request.client else "unknown"
    await rate_limits.enforce(redis, key=f"ypgym:rate:oauth-link-password:{hash_token(client)}", limit=10, window_seconds=900)
    return await OAuthService(session, redis).confirm_pending_with_password(code=payload.code, password=payload.password)


@auth_router.post("/oauth/link/email", response_model=PendingLinkEmailResponse)
async def pending_link_email(
    payload: PendingLinkRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> PendingLinkEmailResponse:
    client = request.client.host if request.client else "unknown"
    await rate_limits.enforce(redis, key=f"ypgym:rate:oauth-link-email:{hash_token(client)}", limit=5, window_seconds=900)
    await OAuthService(session, redis).queue_pending_email(code=payload.code)
    return PendingLinkEmailResponse(message="A secure confirmation email has been queued.")


@auth_router.post("/oauth/link/email/confirm", response_model=LoginResponse)
async def pending_link_email_confirm(
    payload: PendingLinkEmailConfirmRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> LoginResponse:
    client = request.client.host if request.client else "unknown"
    await rate_limits.enforce(redis, key=f"ypgym:rate:oauth-link-confirm:{hash_token(client)}", limit=20, window_seconds=900)
    return await OAuthService(session, redis).confirm_pending_with_email(payload.token)


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
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    platform: Platform = Query("web"),
) -> OAuthStartResponse:
    client = request.client.host if request.client else "unknown"
    await rate_limits.enforce(redis, key=f"ypgym:rate:oauth-link-start:{hash_token(client)}", limit=10, window_seconds=300)
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
