from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import ExternalIdentity, OAuthPendingLink


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


class OAuthPendingLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_code_hash(self, code_hash: str, *, for_update: bool = False) -> OAuthPendingLink | None:
        query = select(OAuthPendingLink).where(OAuthPendingLink.code_hash == code_hash)
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_by_email_token_hash(self, token_hash: str, *, for_update: bool = False) -> OAuthPendingLink | None:
        query = select(OAuthPendingLink).where(OAuthPendingLink.email_token_hash == token_hash)
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_by_id(self, pending_id: UUID, *, for_update: bool = False) -> OAuthPendingLink | None:
        query = select(OAuthPendingLink).where(OAuthPendingLink.id == pending_id)
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def claim_email(self, *, now: datetime, max_attempts: int, stale_seconds: int = 900) -> OAuthPendingLink | None:
        stale_before = now - timedelta(seconds=stale_seconds)
        await self.session.execute(
            update(OAuthPendingLink)
            .where(
                OAuthPendingLink.email_delivery_state == "sending",
                OAuthPendingLink.email_last_attempt_at <= stale_before,
                OAuthPendingLink.email_attempt_count < max_attempts,
            )
            .values(email_delivery_state="retrying", email_next_attempt_at=now, email_error_code="stale_claim")
        )
        await self.session.execute(
            update(OAuthPendingLink)
            .where(
                OAuthPendingLink.email_delivery_state == "sending",
                OAuthPendingLink.email_last_attempt_at <= stale_before,
                OAuthPendingLink.email_attempt_count >= max_attempts,
            )
            .values(email_delivery_state="failed", email_next_attempt_at=None, email_error_code="stale_claim_exhausted")
        )
        item = (
            await self.session.execute(
                select(OAuthPendingLink)
                .where(
                    OAuthPendingLink.consumed_at.is_(None),
                    OAuthPendingLink.expires_at > now,
                    or_(
                        OAuthPendingLink.email_delivery_state == "queued",
                        (OAuthPendingLink.email_delivery_state == "retrying")
                        & (OAuthPendingLink.email_attempt_count < max_attempts)
                        & (OAuthPendingLink.email_next_attempt_at <= now),
                    ),
                )
                .order_by(OAuthPendingLink.created_at)
                .with_for_update(skip_locked=True)
                .limit(1),
            )
        ).scalar_one_or_none()
        if item:
            item.email_delivery_state = "sending"
            item.email_attempt_count += 1
            item.email_last_attempt_at = now
        return item

    async def supersede_active(self, *, user_id: UUID, provider: str, subject: str, now: datetime) -> None:
        await self.session.execute(
            update(OAuthPendingLink)
            .where(
                OAuthPendingLink.user_id == user_id,
                OAuthPendingLink.provider == provider,
                OAuthPendingLink.provider_subject == subject,
                OAuthPendingLink.consumed_at.is_(None),
            )
            .values(consumed_at=now, link_method="superseded", email_delivery_state="cancelled")
        )
