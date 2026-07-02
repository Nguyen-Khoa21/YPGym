from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
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
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LoginResponse:
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
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ForgotPasswordResponse:
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
