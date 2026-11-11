from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.operations import AuditLog
from app.models.user import User


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        action: str,
        entity_type: str,
        summary: str,
        actor_user_id: UUID | None = None,
        target_user_id: UUID | None = None,
        entity_id: str | None = None,
        reason: str | None = None,
        outcome: str | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
    ) -> AuditLog:
        item = AuditLog(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            reason=reason,
            outcome=outcome,
            summary=summary,
            before_data=before_data,
            after_data=after_data,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def list_filtered(
        self,
        *,
        page: int,
        page_size: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        action: str | None = None,
        actor: str | None = None,
        target: str | None = None,
        entity: str | None = None,
    ) -> tuple[list[tuple[AuditLog, str | None, str | None]], int]:
        actor_user = aliased(User)
        target_user = aliased(User)
        conditions = []
        if date_from:
            conditions.append(AuditLog.created_at >= date_from)
        if date_to:
            conditions.append(AuditLog.created_at <= date_to)
        if action:
            conditions.append(AuditLog.action.ilike(f"%{action.strip()}%"))
        if actor:
            term = f"%{actor.strip()}%"
            conditions.append(or_(actor_user.name.ilike(term), actor_user.email.ilike(term)))
        if target:
            term = f"%{target.strip()}%"
            conditions.append(or_(target_user.name.ilike(term), target_user.email.ilike(term)))
        if entity:
            term = f"%{entity.strip()}%"
            conditions.append(or_(AuditLog.entity_type.ilike(term), AuditLog.entity_id.ilike(term)))

        joins = (
            AuditLog.__table__
            .outerjoin(actor_user, AuditLog.actor_user_id == actor_user.id)
            .outerjoin(target_user, AuditLog.target_user_id == target_user.id)
        )
        count_query = select(func.count(AuditLog.id)).select_from(joins).where(*conditions)
        total = int((await self.session.execute(count_query)).scalar_one())
        query = (
            select(AuditLog, actor_user.name, target_user.name)
            .select_from(joins)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.session.execute(query)).all()
        return [(row[0], row[1], row[2]) for row in rows], total

    async def list_for_target(self, user_id: UUID, limit: int = 30) -> list[tuple[AuditLog, str | None]]:
        actor = aliased(User)
        rows = (
            await self.session.execute(
                select(AuditLog, actor.name)
                .outerjoin(actor, AuditLog.actor_user_id == actor.id)
                .where(AuditLog.target_user_id == user_id)
                .order_by(AuditLog.created_at.desc())
                .limit(limit),
            )
        ).all()
        return [(row[0], row[1]) for row in rows]
