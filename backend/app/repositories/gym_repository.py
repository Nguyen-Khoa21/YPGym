from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gym import GymLocation, WorkforceGymAssignment
from app.models.user import User


class GymRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_locations(self, *, active_only: bool) -> list[GymLocation]:
        query = select(GymLocation)
        if active_only:
            query = query.where(GymLocation.is_active.is_(True))
        result = await self.session.execute(query.order_by(GymLocation.name, GymLocation.id))
        return list(result.scalars().all())

    async def get_location(self, gym_id: UUID, *, active_only: bool = False) -> GymLocation | None:
        query = select(GymLocation).where(GymLocation.id == gym_id)
        if active_only:
            query = query.where(GymLocation.is_active.is_(True))
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> GymLocation | None:
        return (
            await self.session.execute(select(GymLocation).where(GymLocation.slug == slug))
        ).scalar_one_or_none()

    async def create_location(self, **values) -> GymLocation:
        location = GymLocation(**values)
        self.session.add(location)
        await self.session.flush()
        return location

    async def active_assignment(self, user_id: UUID, *, for_update: bool = False) -> WorkforceGymAssignment | None:
        query = select(WorkforceGymAssignment).where(
            WorkforceGymAssignment.user_id == user_id,
            WorkforceGymAssignment.is_active.is_(True),
        )
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def list_assignments(
        self,
        *,
        gym_id: UUID | None = None,
    ) -> list[tuple[WorkforceGymAssignment, User, GymLocation]]:
        query = (
            select(WorkforceGymAssignment, User, GymLocation)
            .join(User, User.id == WorkforceGymAssignment.user_id)
            .join(GymLocation, GymLocation.id == WorkforceGymAssignment.gym_id)
            .where(WorkforceGymAssignment.is_active.is_(True))
        )
        if gym_id is not None:
            query = query.where(WorkforceGymAssignment.gym_id == gym_id)
        result = await self.session.execute(query.order_by(GymLocation.name, User.name, User.id))
        return list(result.all())

    async def assign(self, *, user: User, gym: GymLocation) -> WorkforceGymAssignment:
        current = await self.active_assignment(user.id, for_update=True)
        if current and current.gym_id == gym.id and current.assigned_role == user.role:
            return current
        if current:
            current.is_active = False
        assignment = WorkforceGymAssignment(
            user_id=user.id,
            gym_id=gym.id,
            assigned_role=user.role,
            is_active=True,
        )
        self.session.add(assignment)
        await self.session.flush()
        return assignment
