from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classes import PersonalTrainer
from app.models.staff import StaffShift
from app.models.user import User


class StaffRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_accounts(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        role: str | None,
    ) -> tuple[list[tuple[User, UUID | None]], int]:
        conditions = [User.role.in_(("staff", "pt"))]
        if role:
            conditions.append(User.role == role)
        if search:
            term = f"%{search.strip()}%"
            conditions.append(or_(User.name.ilike(term), User.email.ilike(term)))
        total = int(
            (
                await self.session.execute(
                    select(func.count(User.id)).where(*conditions),
                )
            ).scalar_one()
        )
        rows = (
            await self.session.execute(
                select(User, PersonalTrainer.id)
                .outerjoin(PersonalTrainer, PersonalTrainer.user_id == User.id)
                .where(*conditions)
                .order_by(User.created_at.desc(), User.id)
                .offset((page - 1) * page_size)
                .limit(page_size),
            )
        ).all()
        return [(row[0], row[1]) for row in rows], total

    async def trainer_id_for_user(self, user_id: UUID) -> UUID | None:
        return (
            await self.session.execute(
                select(PersonalTrainer.id).where(PersonalTrainer.user_id == user_id),
            )
        ).scalar_one_or_none()

    async def create_shift(self, *, user_id: UUID, clocked_in_at: datetime) -> StaffShift:
        shift = StaffShift(user_id=user_id, clocked_in_at=clocked_in_at)
        self.session.add(shift)
        await self.session.flush()
        return shift

    async def open_shift(self, user_id: UUID, *, for_update: bool = False) -> StaffShift | None:
        query = select(StaffShift).where(
            StaffShift.user_id == user_id,
            StaffShift.clocked_out_at.is_(None),
        )
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def recent_shifts(self, user_id: UUID, *, limit: int = 10) -> list[StaffShift]:
        return list(
            (
                await self.session.execute(
                    select(StaffShift)
                    .where(StaffShift.user_id == user_id)
                    .order_by(StaffShift.clocked_in_at.desc())
                    .limit(limit),
                )
            ).scalars().all()
        )

    async def list_shifts(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        role: str | None,
        status: str | None,
        date_from: datetime | None,
        date_to_exclusive: datetime | None,
    ) -> tuple[list[tuple[StaffShift, User]], int]:
        conditions = [User.role.in_(("staff", "pt"))]
        if search:
            term = f"%{search.strip()}%"
            conditions.append(or_(User.name.ilike(term), User.email.ilike(term)))
        if role:
            conditions.append(User.role == role)
        if status == "open":
            conditions.append(StaffShift.clocked_out_at.is_(None))
        elif status == "closed":
            conditions.append(StaffShift.clocked_out_at.is_not(None))
        if date_from:
            conditions.append(StaffShift.clocked_in_at >= date_from)
        if date_to_exclusive:
            conditions.append(StaffShift.clocked_in_at < date_to_exclusive)
        joined = StaffShift.__table__.join(User, User.id == StaffShift.user_id)
        total = int(
            (
                await self.session.execute(
                    select(func.count(StaffShift.id)).select_from(joined).where(*conditions),
                )
            ).scalar_one()
        )
        rows = (
            await self.session.execute(
                select(StaffShift, User)
                .join(User, User.id == StaffShift.user_id)
                .where(*conditions)
                .order_by(StaffShift.clocked_in_at.desc(), StaffShift.id)
                .offset((page - 1) * page_size)
                .limit(page_size),
            )
        ).all()
        return [(row[0], row[1]) for row in rows], total
