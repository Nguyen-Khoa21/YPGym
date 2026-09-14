from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.rate_limit import rate_limits
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth_schema import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    UserPublic,
    VerifyEmailResponse,
)
from app.services.auth_service import AuthService
from app.utils.security import hash_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RegisterResponse:
    return await AuthService(session).register(payload)


@router.get("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    token: Annotated[str, Query(min_length=16)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> VerifyEmailResponse:
    return await AuthService(session).verify_email(token)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> LoginResponse:
    client = request.client.host if request.client else "unknown"
    await rate_limits.enforce(redis, key=f"ypgym:rate:login:ip:{hash_token(client)}", limit=60, window_seconds=60)
    rate_key = hash_token(f"{client}:{payload.email.lower()}")
    await rate_limits.enforce(
        redis,
        key=f"ypgym:rate:login:{rate_key}",
        limit=10,
        window_seconds=60,
    )
    return await AuthService(session).login(
        email=payload.email,
        password=payload.password,
    )


@router.get("/me", response_model=UserPublic)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> ForgotPasswordResponse:
    client = request.client.host if request.client else "unknown"
    await rate_limits.enforce(redis, key=f"ypgym:rate:forgot:ip:{hash_token(client)}", limit=20, window_seconds=900)
    rate_key = hash_token(f"{client}:{payload.email.lower()}")
    await rate_limits.enforce(
        redis,
        key=f"ypgym:rate:forgot:{rate_key}",
        limit=5,
        window_seconds=900,
    )
    return await AuthService(session).forgot_password(payload.email)


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResetPasswordResponse:
    return await AuthService(session).reset_password(
        token=payload.token,
        new_password=payload.new_password,
    )
