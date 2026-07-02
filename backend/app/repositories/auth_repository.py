from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_token import EmailVerification, PasswordReset


class AuthTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_email_verification(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        new_email: str | None = None,
    ) -> EmailVerification:
        record = EmailVerification(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            new_email=new_email,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_email_verification_by_hash(
        self,
        token_hash: str,
    ) -> EmailVerification | None:
        result = await self.session.execute(
            select(EmailVerification).where(EmailVerification.token_hash == token_hash),
        )
        return result.scalar_one_or_none()

    async def create_password_reset(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordReset:
        record = PasswordReset(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_password_reset_by_hash(self, token_hash: str) -> PasswordReset | None:
        result = await self.session.execute(
            select(PasswordReset).where(PasswordReset.token_hash == token_hash),
        )
        return result.scalar_one_or_none()
