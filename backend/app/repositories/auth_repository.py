from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
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
        code_hash: str | None = None,
    ) -> EmailVerification:
        record = EmailVerification(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            new_email=new_email,
            code_hash=code_hash,
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

    async def get_latest_open_code(self, user_id: UUID, *, for_update: bool = False) -> EmailVerification | None:
        query = (
            select(EmailVerification)
            .where(
                EmailVerification.user_id == user_id,
                EmailVerification.used_at.is_(None),
                EmailVerification.new_email.is_(None),
                EmailVerification.code_hash.is_not(None),
            )
            .order_by(EmailVerification.created_at.desc())
            .limit(1)
        )
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def expire_open_signup_verifications(self, user_id: UUID, *, now: datetime) -> None:
        """Supersede earlier sign-up codes and links; email-change rows are left alone."""
        await self.session.execute(
            update(EmailVerification)
            .where(
                EmailVerification.user_id == user_id,
                EmailVerification.used_at.is_(None),
                EmailVerification.new_email.is_(None),
                EmailVerification.expires_at > now,
            )
            .values(expires_at=now, code_hash=None)
        )

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
