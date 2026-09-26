from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import ExternalIdentity


class ExternalIdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_subject(self, provider: str, subject: str, *, include_revoked: bool = False) -> ExternalIdentity | None:
        query = select(ExternalIdentity).where(
            ExternalIdentity.provider == provider,
            ExternalIdentity.provider_subject == subject,
        )
        if not include_revoked:
            query = query.where(ExternalIdentity.revoked_at.is_(None))
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_for_user_provider(self, user_id: UUID, provider: str) -> ExternalIdentity | None:
        return (
            await self.session.execute(
                select(ExternalIdentity).where(
                    ExternalIdentity.user_id == user_id,
                    ExternalIdentity.provider == provider,
                ),
            )
        ).scalar_one_or_none()

    async def list_active(self, user_id: UUID) -> list[ExternalIdentity]:
        return list(
            (
                await self.session.execute(
                    select(ExternalIdentity)
                    .where(ExternalIdentity.user_id == user_id, ExternalIdentity.revoked_at.is_(None))
                    .order_by(ExternalIdentity.provider),
                )
            ).scalars().all(),
        )

    async def attach(self, *, user_id: UUID, provider: str, subject: str, email: str | None, email_verified: bool) -> ExternalIdentity:
        existing = await self.get_for_user_provider(user_id, provider)
        if existing:
            existing.provider_subject = subject
            existing.provider_email = email
            existing.provider_email_verified = email_verified
            existing.revoked_at = None
            existing.last_login_at = datetime.now(UTC)
            await self.session.flush()
            return existing
        identity = ExternalIdentity(
            user_id=user_id,
            provider=provider,
            provider_subject=subject,
            provider_email=email,
            provider_email_verified=email_verified,
            last_login_at=datetime.now(UTC),
        )
        self.session.add(identity)
        await self.session.flush()
        return identity
