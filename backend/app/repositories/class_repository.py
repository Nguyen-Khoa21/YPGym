from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classes import GymClass, PersonalTrainer


class ClassRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_trainers(self, *, active_only: bool = True) -> list[PersonalTrainer]:
        query = select(PersonalTrainer)
        if active_only:
            query = query.where(PersonalTrainer.is_active.is_(True))
        return list((await self.session.execute(query.order_by(PersonalTrainer.display_name))).scalars().all())

    async def get_trainer(self, trainer_id: UUID) -> PersonalTrainer | None:
        return await self.session.get(PersonalTrainer, trainer_id)

    async def get_class(self, class_id: UUID, *, for_update: bool = False) -> GymClass | None:
        query = select(GymClass).where(GymClass.id == class_id)
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def list_classes(
        self,
        *,
        page: int,
        page_size: int,
        date_from: datetime | None,
        date_to: datetime | None,
        status: str | None,
        trainer_id: UUID | None,
        search: str | None,
    ) -> tuple[list[tuple[GymClass, str | None]], int, int, int]:
        conditions = []
        if date_from:
            conditions.append(GymClass.start_at >= date_from)
        if date_to:
            conditions.append(GymClass.start_at <= date_to)
        if status:
            conditions.append(GymClass.status == status)
        if trainer_id:
            conditions.append(GymClass.trainer_id == trainer_id)
        if search:
            term = f"%{search.strip()}%"
            conditions.append(or_(GymClass.title.ilike(term), GymClass.class_type.ilike(term)))
        base = GymClass.__table__.outerjoin(PersonalTrainer, PersonalTrainer.id == GymClass.trainer_id)
        summary = (
            await self.session.execute(
                select(
                    func.count(GymClass.id),
                    func.count(GymClass.id).filter(GymClass.status == "scheduled"),
                    func.count(GymClass.id).filter(GymClass.status == "cancelled"),
                )
                .select_from(base)
                .where(*conditions),
            )
        ).one()
        rows = (
            await self.session.execute(
                select(GymClass, PersonalTrainer.display_name)
                .select_from(base)
                .where(*conditions)
                .order_by(GymClass.start_at.asc(), GymClass.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size),
            )
        ).all()
        return [(row[0], row[1]) for row in rows], int(summary[0]), int(summary[1]), int(summary[2])

    async def find_overlap(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        location: str,
        trainer_id: UUID | None,
        exclude_id: UUID | None = None,
    ) -> GymClass | None:
        resource_conflict = GymClass.location == location
        if trainer_id:
            resource_conflict = or_(resource_conflict, GymClass.trainer_id == trainer_id)
        conditions = [
            GymClass.status == "scheduled",
            GymClass.start_at < end_at,
            GymClass.end_at > start_at,
            resource_conflict,
        ]
        if exclude_id:
            conditions.append(GymClass.id != exclude_id)
        return (
            await self.session.execute(
                select(GymClass).where(*conditions).order_by(GymClass.start_at).limit(1),
            )
        ).scalar_one_or_none()

    async def create_class(self, **values) -> GymClass:
        item = GymClass(**values)
        self.session.add(item)
        await self.session.flush()
        return item
