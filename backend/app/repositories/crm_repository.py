from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models.attendance import AttendanceSession
from app.models.billing import Invoice, Payment
from app.models.classes import ClassBooking, ClassWaitlist, GymClass
from app.models.gym import WorkforceGymAssignment
from app.models.membership import MembershipPlan, UserMembership
from app.models.user import User


def gym_member_clause(gym_id: UUID, home_gym_column):
    """A user belongs to a gym through their latest membership's home gym, or through an active workforce assignment."""
    assigned = select(WorkforceGymAssignment.user_id).where(
        WorkforceGymAssignment.gym_id == gym_id,
        WorkforceGymAssignment.is_active.is_(True),
    )
    return or_(home_gym_column == gym_id, User.id.in_(assigned))


def latest_membership_subquery():
    return (
        select(
            UserMembership.id.label("membership_id"),
            UserMembership.user_id.label("user_id"),
            func.row_number()
            .over(
                partition_by=UserMembership.user_id,
                order_by=(UserMembership.expiry_date.desc(), UserMembership.created_at.desc()),
            )
            .label("row_number"),
        )
        .subquery()
    )


class CrmRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _member_conditions(
        self,
        *,
        membership: type[UserMembership],
        search: str | None,
        role: str | None,
        tier: str | None,
        status: str | None,
        expiry_from: date | None,
        expiry_to: date | None,
    ) -> list[Any]:
        conditions: list[Any] = []
        if search:
            term = f"%{search.strip()}%"
            conditions.append(or_(User.name.ilike(term), User.email.ilike(term), User.phone.ilike(term)))
        if role:
            conditions.append(User.role == role)
        if tier:
            conditions.append(User.tier == tier)
        if status:
            conditions.append(membership.status == status)
        if expiry_from:
            conditions.append(membership.expiry_date >= expiry_from)
        if expiry_to:
            conditions.append(membership.expiry_date <= expiry_to)
        return conditions

    async def list_members(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        role: str | None,
        tier: str | None,
        status: str | None,
        expiry_from: date | None,
        expiry_to: date | None,
        sort_by: str,
        sort_order: str,
        gym_id: UUID | None = None,
    ) -> tuple[list[tuple[User, UserMembership | None, MembershipPlan | None]], int, tuple[int, int, int, int, int]]:
        latest = latest_membership_subquery()
        membership = aliased(UserMembership)
        plan = aliased(MembershipPlan)
        joins = (
            User.__table__
            .outerjoin(latest, and_(latest.c.user_id == User.id, latest.c.row_number == 1))
            .outerjoin(membership, membership.id == latest.c.membership_id)
            .outerjoin(plan, plan.id == membership.plan_id)
        )
        conditions = self._member_conditions(
            membership=membership,
            search=search,
            role=role,
            tier=tier,
            status=status,
            expiry_from=expiry_from,
            expiry_to=expiry_to,
        )
        if gym_id is not None:
            conditions.append(gym_member_clause(gym_id, membership.home_gym_id))
        total = int(
            (
                await self.session.execute(
                    select(func.count(User.id)).select_from(joins).where(*conditions),
                )
            ).scalar_one(),
        )
        summary_row = (
            await self.session.execute(
                select(
                    func.count(User.id),
                    func.count(User.id).filter(membership.status == "active"),
                    func.count(User.id).filter(membership.status == "expiring_soon"),
                    func.count(User.id).filter(membership.status == "frozen"),
                    func.count(User.id).filter(or_(membership.id.is_(None), membership.status.in_(("expired", "cancelled", "revoked")))),
                )
                .select_from(joins)
                .where(*conditions),
            )
        ).one()
        sort_map = {
            "name": User.name,
            "email": User.email,
            "created_at": User.created_at,
            "expiry_date": membership.expiry_date,
            "status": membership.status,
        }
        sort_column = sort_map[sort_by]
        ordering = sort_column.desc().nullslast() if sort_order == "desc" else sort_column.asc().nullslast()
        rows = (
            await self.session.execute(
                select(User, membership, plan)
                .select_from(joins)
                .where(*conditions)
                .order_by(ordering, User.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size),
            )
        ).all()
        return [(row[0], row[1], row[2]) for row in rows], total, tuple(int(value or 0) for value in summary_row)

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def user_in_gym(self, user_id: UUID, gym_id: UUID) -> bool:
        latest = latest_membership_subquery()
        membership = aliased(UserMembership)
        joins = (
            User.__table__
            .outerjoin(latest, and_(latest.c.user_id == User.id, latest.c.row_number == 1))
            .outerjoin(membership, membership.id == latest.c.membership_id)
        )
        found = await self.session.execute(
            select(User.id).select_from(joins).where(User.id == user_id, gym_member_clause(gym_id, membership.home_gym_id)),
        )
        return found.first() is not None

    async def list_memberships(self, user_id: UUID) -> list[UserMembership]:
        return list(
            (
                await self.session.execute(
                    select(UserMembership)
                    .options(selectinload(UserMembership.plan))
                    .where(UserMembership.user_id == user_id)
                    .order_by(UserMembership.expiry_date.desc()),
                )
            ).scalars().all(),
        )

    async def list_payments(self, user_id: UUID) -> list[Payment]:
        return list(
            (
                await self.session.execute(
                    select(Payment)
                    .options(
                        selectinload(Payment.plan),
                        selectinload(Payment.class_booking).selectinload(ClassBooking.gym_class),
                    )
                    .where(Payment.user_id == user_id)
                    .order_by(Payment.created_at.desc()),
                )
            ).scalars().all(),
        )

    async def list_invoices(self, user_id: UUID) -> list[Invoice]:
        return list(
            (
                await self.session.execute(
                    select(Invoice)
                    .where(Invoice.user_id == user_id)
                    .order_by(Invoice.transaction_date.desc()),
                )
            ).scalars().all(),
        )

    async def attendance_summary(self, user_id: UUID) -> tuple[int, int, datetime | None]:
        row = (
            await self.session.execute(
                select(
                    func.count(AttendanceSession.id),
                    func.count(AttendanceSession.id).filter(AttendanceSession.status == "active"),
                    func.max(AttendanceSession.checked_in_at),
                ).where(AttendanceSession.user_id == user_id),
            )
        ).one()
        return int(row[0] or 0), int(row[1] or 0), row[2]

    async def attendance_history(self, user_id: UUID, limit: int = 20) -> list[AttendanceSession]:
        return list(
            (
                await self.session.execute(
                    select(AttendanceSession)
                    .where(AttendanceSession.user_id == user_id)
                    .order_by(AttendanceSession.checked_in_at.desc())
                    .limit(limit),
                )
            ).scalars().all(),
        )

    async def booking_summary(self, user_id: UUID) -> tuple[int, int, int]:
        total = int(
            (
                await self.session.execute(
                    select(func.count(ClassBooking.id)).where(ClassBooking.user_id == user_id),
                )
            ).scalar_one(),
        )
        upcoming = int(
            (
                await self.session.execute(
                    select(func.count(ClassBooking.id))
                    .join(GymClass, GymClass.id == ClassBooking.class_id)
                    .where(
                        ClassBooking.user_id == user_id,
                        ClassBooking.status == "confirmed",
                        GymClass.start_at > func.now(),
                    ),
                )
            ).scalar_one(),
        )
        waitlisted = int(
            (
                await self.session.execute(
                    select(func.count(ClassWaitlist.id)).where(
                        ClassWaitlist.user_id == user_id,
                        ClassWaitlist.status == "waiting",
                    ),
                )
            ).scalar_one(),
        )
        return total, upcoming, waitlisted
