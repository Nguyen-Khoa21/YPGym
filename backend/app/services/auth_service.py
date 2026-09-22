import asyncio
import logging
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, DependencyUnavailableError
from app.models.enums import MemberTier, UserRole
from app.models.user import User
from app.repositories.auth_repository import AuthTokenRepository
from app.repositories.operations_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.services.email_service import ConfiguredEmailTransport
from app.schemas.auth_schema import (
    ForgotPasswordResponse,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordResponse,
    UserPublic,
    VerifyEmailResponse,
)
from app.utils.security import (
    create_access_token,
    generate_url_token,
    hash_password,
    hash_token,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.tokens = AuthTokenRepository(session)
        self.notifications = NotificationRepository(session)
        self.settings = get_settings()

    async def register(self, payload: RegisterRequest) -> RegisterResponse:
        email = payload.email.lower()
        phone = payload.phone.strip()

        if await self.users.get_by_email(email):
            raise AppError(
                code="EMAIL_ALREADY_EXISTS",
                message="An account with this email already exists.",
                status_code=409,
            )

        if await self.users.get_by_phone(phone):
            raise AppError(
                code="PHONE_ALREADY_EXISTS",
                message="An account with this phone number already exists.",
                status_code=409,
            )

        try:
            user = await self.users.create(
                name=payload.name.strip(),
                email=email,
                phone=phone,
                password_hash=hash_password(payload.password),
                role=UserRole.MEMBER.value,
                tier=MemberTier.NORMAL.value,
                is_email_verified=False,
            )
            verification_token = await self._create_email_verification(user)
            await self.notifications.create_notification_once(
                user_id=user.id,
                category="account",
                notification_type="registration_welcome",
                title="Welcome to YPGym",
                message="Welcome to YPGym. Verify your email, then explore membership plans and member features.",
                channel="email",
                delivery_state="pending",
                dedupe_key=f"registration-welcome:{user.id}:email",
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError(
                code="REGISTRATION_CONFLICT",
                message="The account could not be registered because the email or phone is already used.",
                status_code=409,
            ) from exc

        try:
            await self._prepare_development_email(user.email, "Email verification", "/verify-email", verification_token)
        except DependencyUnavailableError as exc:
            logger.warning(
                "registration_verification_email_failed user_id=%s exception_type=%s",
                user.id,
                type(exc).__name__,
            )
        return RegisterResponse(
            message="Registration successful. Please verify your email before logging in.",
            user=UserPublic.model_validate(user),
        )

    async def verify_email(self, token: str) -> VerifyEmailResponse:
        record = await self.tokens.get_email_verification_by_hash(hash_token(token))
        now = datetime.now(UTC)

        if record is None:
            raise AppError("INVALID_VERIFICATION_TOKEN", "The verification link is invalid.", 400)

        user = await self.users.get_by_id(record.user_id)
        if user is None:
            raise AppError("INVALID_VERIFICATION_TOKEN", "The verification link is invalid.", 400)

        if record.used_at:
            return VerifyEmailResponse(
                message="Email is already verified.",
                user=UserPublic.model_validate(user),
            )

        if record.expires_at < now:
            raise AppError("VERIFICATION_TOKEN_EXPIRED", "The verification link has expired.", 400)

        if record.new_email:
            existing = await self.users.get_by_email(record.new_email)
            if existing and existing.id != user.id:
                raise AppError(
                    "EMAIL_ALREADY_EXISTS",
                    "This email address is already used by another account.",
                    409,
                )
            user.email = record.new_email.lower()
            user.pending_email = None

        user.is_email_verified = True
        user.email_verified_at = now
        record.used_at = now
        await self.session.commit()
        await self.session.refresh(user)

        return VerifyEmailResponse(
            message="Email verified successfully.",
            user=UserPublic.model_validate(user),
        )

    async def login(self, *, email: str, password: str) -> LoginResponse:
        user = await self.users.get_by_email(email.lower())
        if not user or not verify_password(password, user.password_hash):
            raise AppError(
                "INVALID_CREDENTIALS",
                "The email or password is incorrect.",
                401,
            )

        if not user.is_email_verified:
            raise AppError(
                "EMAIL_NOT_VERIFIED",
                "Please verify your email before logging in.",
                403,
            )

        access_token, expires_at = create_access_token(
            user_id=user.id,
            role=user.role,
            tier=user.tier,
        )
        return LoginResponse(
            access_token=access_token,
            expires_at=expires_at,
            user=UserPublic.model_validate(user),
        )

    async def forgot_password(self, email: str) -> ForgotPasswordResponse:
        user = await self.users.get_by_email(email.lower())
        if user and user.is_email_verified:
            token = generate_url_token()
            expires_at = datetime.now(UTC) + timedelta(
                minutes=self.settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
            )
            await self.tokens.create_password_reset(
                user_id=user.id,
                token_hash=hash_token(token),
                expires_at=expires_at,
            )
            await self.session.commit()
            try:
                await self._prepare_development_email(user.email, "Password reset", "/reset-password", token)
            except DependencyUnavailableError as exc:
                logger.warning(
                    "password_reset_email_failed user_id=%s exception_type=%s",
                    user.id,
                    type(exc).__name__,
                )

        return ForgotPasswordResponse(
            message="If this email is registered, a password reset link has been prepared.",
        )

    async def reset_password(self, *, token: str, new_password: str) -> ResetPasswordResponse:
        record = await self.tokens.get_password_reset_by_hash(hash_token(token))
        now = datetime.now(UTC)

        if record is None or record.used_at:
            raise AppError("INVALID_RESET_TOKEN", "The password reset link is invalid.", 400)

        if record.expires_at < now:
            raise AppError("RESET_TOKEN_EXPIRED", "The password reset link has expired.", 400)

        user = await self.users.get_by_id(record.user_id)
        if user is None:
            raise AppError("INVALID_RESET_TOKEN", "The password reset link is invalid.", 400)

        user.password_hash = hash_password(new_password)
        record.used_at = now
        await self.session.commit()

        return ResetPasswordResponse(message="Password reset successful. You can log in now.")

    async def _create_email_verification(self, user: User) -> str:
        token = generate_url_token()
        expires_at = datetime.now(UTC) + timedelta(
            hours=self.settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
        )
        await self.tokens.create_email_verification(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=expires_at,
        )
        return token

    async def _prepare_development_email(self, recipient: str, label: str, route: str, token: str) -> None:
        if self.settings.EMAIL_DELIVERY_MODE == "development" and self.settings.ENVIRONMENT != "development":
            return
        message = EmailMessage()
        message["From"] = formataddr((self.settings.EMAIL_SENDER_NAME, self.settings.EMAIL_SENDER_ADDRESS))
        message["To"] = recipient
        message["Subject"] = f"YPGym: {label}"
        links = [f"{self.settings.FRONTEND_URL.rstrip('/')}{route}?token={token}"]
        if route == "/verify-email":
            links.append(f"{self.settings.MOBILE_APP_URL}{route.lstrip('/')}?token={token}")
        message.set_content("\n".join(links) + "\n")

        try:
            await asyncio.to_thread(ConfiguredEmailTransport(self.settings).send, message)
        except (OSError, smtplib.SMTPException) as exc:
            raise DependencyUnavailableError(
                "EMAIL_DELIVERY_UNAVAILABLE",
                "The email could not be delivered. Check the mail configuration.",
            ) from exc
