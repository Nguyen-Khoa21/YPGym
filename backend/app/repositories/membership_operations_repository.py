from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.membership import UserMembership
from app.models.operations import MembershipCancellationRequest, MembershipFreezeRequest
from app.models.user import User


class MembershipOperationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_current_for_update(self, user_id: UUID) -> UserMembership | None:
        result = await self.session.execute(
            select(UserMembership)
            .where(UserMembership.user_id == user_id)
            .order_by(UserMembership.expiry_date.desc(), UserMembership.created_at.desc())
            .with_for_update(),
        )
        return result.scalars().first()

    async def get_latest(self, user_id: UUID) -> UserMembership | None:
        result = await self.session.execute(
            select(UserMembership)
            .options(selectinload(UserMembership.plan))
            .where(UserMembership.user_id == user_id)
            .order_by(UserMembership.expiry_date.desc(), UserMembership.created_at.desc()),
        )
        return result.scalars().first()

    async def list_lifecycle_candidates(self) -> list[tuple[UserMembership, bool]]:
        rows = (
            await self.session.execute(
                select(UserMembership, User.is_email_verified)
                .join(User, User.id == UserMembership.user_id)
                .where(UserMembership.status.not_in(("cancelled", "revoked"))),
            )
        ).all()
        return [(row[0], bool(row[1])) for row in rows]

    async def create_freeze_request(
        self,
        *,
        membership: UserMembership,
        start_date: date,
        end_date: date,
        reason: str,
    ) -> MembershipFreezeRequest:
        request = MembershipFreezeRequest(
            membership_id=membership.id,
            user_id=membership.user_id,
            requested_start_date=start_date,
            requested_end_date=end_date,
            reason=reason,
            status="pending",
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_freeze_request_for_update(self, request_id: UUID) -> MembershipFreezeRequest | None:
        result = await self.session.execute(
            select(MembershipFreezeRequest)
            .where(MembershipFreezeRequest.id == request_id)
            .with_for_update(),
        )
        return result.scalar_one_or_none()

    async def create_cancellation_request(
        self,
        *,
        membership: UserMembership,
        reason: str,
    ) -> MembershipCancellationRequest:
        request = MembershipCancellationRequest(
            membership_id=membership.id,
            user_id=membership.user_id,
            reason=reason,
            status="pending",
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_cancellation_request_for_update(
        self,
        request_id: UUID,
    ) -> MembershipCancellationRequest | None:
        result = await self.session.execute(
            select(MembershipCancellationRequest)
            .where(MembershipCancellationRequest.id == request_id)
            .with_for_update(),
        )
        return result.scalar_one_or_none()

    async def list_requests_for_user(
        self,
        user_id: UUID,
    ) -> tuple[list[MembershipFreezeRequest], list[MembershipCancellationRequest]]:
        freezes = list(
            (
                await self.session.execute(
                    select(MembershipFreezeRequest)
                    .where(MembershipFreezeRequest.user_id == user_id)
                    .order_by(MembershipFreezeRequest.created_at.desc()),
                )
            ).scalars().all(),
        )
        cancellations = list(
            (
                await self.session.execute(
                    select(MembershipCancellationRequest)
                    .where(MembershipCancellationRequest.user_id == user_id)
                    .order_by(MembershipCancellationRequest.created_at.desc()),
                )
            ).scalars().all(),
        )
        return freezes, cancellations

    async def list_approval_requests(
        self,
        status: str | None,
        gym_id: UUID | None = None,
    ) -> tuple[
        list[tuple[MembershipFreezeRequest, User]],
        list[tuple[MembershipCancellationRequest, User]],
    ]:
        freeze_query = select(MembershipFreezeRequest, User).join(
            User,
            User.id == MembershipFreezeRequest.user_id,
        )
        cancellation_query = select(MembershipCancellationRequest, User).join(
            User,
            User.id == MembershipCancellationRequest.user_id,
        )
        if gym_id is not None:
            freeze_query = freeze_query.join(UserMembership, UserMembership.id == MembershipFreezeRequest.membership_id).where(UserMembership.home_gym_id == gym_id)
            cancellation_query = cancellation_query.join(UserMembership, UserMembership.id == MembershipCancellationRequest.membership_id).where(UserMembership.home_gym_id == gym_id)
        if status:
            freeze_query = freeze_query.where(MembershipFreezeRequest.status == status)
            cancellation_query = cancellation_query.where(MembershipCancellationRequest.status == status)
        freeze_rows = (await self.session.execute(freeze_query)).all()
        cancellation_rows = (await self.session.execute(cancellation_query)).all()
        return (
            [(row[0], row[1]) for row in freeze_rows],
            [(row[0], row[1]) for row in cancellation_rows],
        )
