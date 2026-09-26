from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Invoice, Payment
from app.models.email_delivery import EmailDelivery
from app.models.membership import UserMembership
from app.models.user import User


class EmailDeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enqueue_once(self, **values: Any) -> bool:
        statement = (
            insert(EmailDelivery)
            .values(**values)
            .on_conflict_do_nothing(constraint="uq_email_deliveries_idempotency_key")
            .returning(EmailDelivery.id)
        )
        return (await self.session.execute(statement)).scalar_one_or_none() is not None

    async def claim_next(self, *, max_attempts: int, stale_seconds: int = 900) -> EmailDelivery | None:
        now = datetime.now(UTC)
        stale_before = now - timedelta(seconds=stale_seconds)
        await self.session.execute(
            update(EmailDelivery)
            .where(
                EmailDelivery.status == "sending",
                EmailDelivery.last_attempt_at <= stale_before,
                EmailDelivery.attempt_count >= max_attempts,
            )
            .values(
                status="failed",
                next_attempt_at=None,
                last_error_category="provider_unavailable",
                last_error_code="stale_claim_exhausted",
            )
        )
        candidate = (
            await self.session.execute(
                select(EmailDelivery)
                .where(
                    or_(
                        EmailDelivery.status == "queued",
                        (EmailDelivery.status == "retrying")
                        & (EmailDelivery.attempt_count < max_attempts)
                        & (EmailDelivery.next_attempt_at <= now),
                        (EmailDelivery.status == "sending")
                        & (EmailDelivery.attempt_count < max_attempts)
                        & (EmailDelivery.last_attempt_at <= stale_before),
                    ),
                )
                .order_by(EmailDelivery.created_at, EmailDelivery.id)
                .with_for_update(skip_locked=True)
                .limit(1),
            )
        ).scalar_one_or_none()
        if candidate:
            candidate.status = "sending"
            candidate.attempt_count += 1
            candidate.last_attempt_at = now
        return candidate

    async def get_context(self, delivery_id: UUID) -> tuple[EmailDelivery, User, UserMembership, Payment, Invoice] | None:
        row = (
            await self.session.execute(
                select(EmailDelivery, User, UserMembership, Payment, Invoice)
                .join(User, User.id == EmailDelivery.user_id)
                .join(UserMembership, UserMembership.id == EmailDelivery.membership_id)
                .join(Payment, Payment.id == EmailDelivery.payment_id)
                .join(Invoice, Invoice.id == EmailDelivery.invoice_id)
                .where(EmailDelivery.id == delivery_id),
            )
        ).first()
        return tuple(row) if row else None

    async def list_admin(
        self, *, page: int, page_size: int, status: str | None, template_type: str | None, member: str | None
    ) -> tuple[list[tuple[EmailDelivery, User, Invoice]], int]:
        conditions = []
        if status:
            conditions.append(EmailDelivery.status == status)
        if template_type:
            conditions.append(EmailDelivery.template_type == template_type)
        if member:
            term = f"%{member.strip()}%"
            conditions.append(or_(User.name.ilike(term), User.email.ilike(term)))
        joins = EmailDelivery.__table__.join(User, User.id == EmailDelivery.user_id).join(Invoice, Invoice.id == EmailDelivery.invoice_id)
        total = int((await self.session.execute(select(func.count(EmailDelivery.id)).select_from(joins).where(*conditions))).scalar_one())
        rows = (
            await self.session.execute(
                select(EmailDelivery, User, Invoice)
                .select_from(joins)
                .where(*conditions)
                .order_by(EmailDelivery.created_at.desc(), EmailDelivery.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size),
            )
        ).all()
        return [(row[0], row[1], row[2]) for row in rows], total

    async def get_for_update(self, delivery_id: UUID) -> EmailDelivery | None:
        return (
            await self.session.execute(
                select(EmailDelivery).where(EmailDelivery.id == delivery_id).with_for_update(),
            )
        ).scalar_one_or_none()
