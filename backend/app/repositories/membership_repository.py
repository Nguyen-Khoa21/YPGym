from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MembershipStatus
from app.models.membership import MembershipPlan, UserMembership


class MembershipPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, plan_id: UUID) -> MembershipPlan | None:
        return await self.session.get(MembershipPlan, plan_id)

    async def get_by_name(self, name: str) -> MembershipPlan | None:
        result = await self.session.execute(
            select(MembershipPlan).where(MembershipPlan.name == name),
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> list[MembershipPlan]:
        result = await self.session.execute(
            select(MembershipPlan)
            .where(MembershipPlan.is_active.is_(True))
            .order_by(MembershipPlan.duration_days, MembershipPlan.display_order),
        )
        return list(result.scalars().all())


class UserMembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, membership_id: UUID) -> UserMembership | None:
        return await self.session.get(UserMembership, membership_id)

    async def get_current_for_user(self, user_id: UUID) -> UserMembership | None:
        active_statuses = (
            MembershipStatus.ACTIVE.value,
            MembershipStatus.EXPIRING_SOON.value,
        )
        result = await self.session.execute(
            select(UserMembership)
            .where(
                UserMembership.user_id == user_id,
                UserMembership.status.in_(active_statuses),
            )
            .order_by(UserMembership.expiry_date.desc()),
        )
        return result.scalars().first()

    async def get_latest_for_user(self, user_id: UUID) -> UserMembership | None:
        result = await self.session.execute(
            select(UserMembership)
            .where(UserMembership.user_id == user_id)
            .order_by(UserMembership.expiry_date.desc(), UserMembership.created_at.desc())
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        status: str,
        start_date,
        expiry_date,
    ) -> UserMembership:
        membership = UserMembership(
            user_id=user_id,
            plan_id=plan_id,
            status=status,
            start_date=start_date,
            expiry_date=expiry_date,
        )
        self.session.add(membership)
        await self.session.flush()
        return membership
