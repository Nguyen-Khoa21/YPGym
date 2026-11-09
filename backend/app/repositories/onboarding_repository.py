from uuid import UUID

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MembershipStatus
from app.models.membership import UserMembership
from app.models.onboarding import MemberOnboardingProfile
from app.models.user import User


class OnboardingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID) -> MemberOnboardingProfile | None:
        return (
            await self.session.execute(
                select(MemberOnboardingProfile).where(MemberOnboardingProfile.user_id == user_id),
            )
        ).scalar_one_or_none()

    def add(self, profile: MemberOnboardingProfile) -> None:
        self.session.add(profile)

    def _complete(self, query: Select, gym_id: UUID | None) -> Select:
        query = query.where(MemberOnboardingProfile.completed_at.is_not(None))
        if gym_id is not None:
            query = query.where(MemberOnboardingProfile.closer_gym_id == gym_id)
        return query

    async def count_members(self) -> int:
        return (await self.session.execute(select(func.count()).select_from(User).where(User.role == "member"))).scalar_one()

    async def count_respondents(self, *, gym_id: UUID | None) -> int:
        query = self._complete(select(func.count()).select_from(MemberOnboardingProfile), gym_id)
        return (await self.session.execute(query)).scalar_one()

    async def answer_counts(self, column_name: str, *, gym_id: UUID | None) -> dict[object, int]:
        column = getattr(MemberOnboardingProfile, column_name)
        query = self._complete(select(column, func.count()).select_from(MemberOnboardingProfile), gym_id)
        rows = (await self.session.execute(query.where(column.is_not(None)).group_by(column))).all()
        return {value: count for value, count in rows}

    async def closer_gym_counts(self) -> dict[UUID, int]:
        return await self.answer_counts("closer_gym_id", gym_id=None)

    async def home_gym_counts(self) -> dict[UUID, int]:
        rows = (
            await self.session.execute(
                select(UserMembership.home_gym_id, func.count(distinct(UserMembership.user_id)))
                .where(
                    UserMembership.status.in_(
                        [MembershipStatus.ACTIVE.value, MembershipStatus.EXPIRING_SOON.value],
                    ),
                )
                .group_by(UserMembership.home_gym_id),
            )
        ).all()
        return {gym_id: count for gym_id, count in rows}
