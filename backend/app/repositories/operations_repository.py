from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models.attendance import AttendanceSession
from app.models.billing import Invoice, Payment
from app.models.classes import ClassBooking, ClassWaitlist, GymClass
from app.models.membership import MembershipPlan, UserMembership
from app.models.operations import (
    AuditLog,
    BroadcastAnnouncement,
    MembershipCancellationRequest,
    MembershipFreezeRequest,
    Notification,
    NotificationPreference,
)
from app.models.system_configuration import SystemConfiguration
from app.models.user import User


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
        if status:
            freeze_query = freeze_query.where(MembershipFreezeRequest.status == status)
            cancellation_query = cancellation_query.where(MembershipCancellationRequest.status == status)
        freeze_rows = (await self.session.execute(freeze_query)).all()
        cancellation_rows = (await self.session.execute(cancellation_query)).all()
        return (
            [(row[0], row[1]) for row in freeze_rows],
            [(row[0], row[1]) for row in cancellation_rows],
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
                    .options(selectinload(Payment.plan))
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
                        ClassBooking.status == "booked",
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


class BillingAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _conditions(
        self,
        *,
        member: str | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        plan: str | None,
        tier: str | None,
    ) -> list[Any]:
        conditions: list[Any] = []
        if member:
            term = f"%{member.strip()}%"
            conditions.append(or_(User.name.ilike(term), User.email.ilike(term)))
        if status:
            conditions.append(Payment.status == status)
        if date_from:
            conditions.append(Payment.created_at >= date_from)
        if date_to:
            conditions.append(Payment.created_at <= date_to)
        if plan:
            conditions.append(MembershipPlan.name.ilike(f"%{plan.strip()}%"))
        if tier:
            conditions.append(User.tier == tier)
        return conditions

    async def list_payments(
        self,
        *,
        page: int,
        page_size: int,
        member: str | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        plan: str | None,
        tier: str | None,
        paginate: bool = True,
    ) -> tuple[list[tuple[Payment, User, MembershipPlan]], int, Decimal]:
        conditions = self._conditions(
            member=member,
            status=status,
            date_from=date_from,
            date_to=date_to,
            plan=plan,
            tier=tier,
        )
        base = Payment.__table__.join(User, User.id == Payment.user_id).join(MembershipPlan, MembershipPlan.id == Payment.plan_id)
        summary = (
            await self.session.execute(
                select(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
                .select_from(base)
                .where(*conditions),
            )
        ).one()
        query = (
            select(Payment, User, MembershipPlan)
            .select_from(base)
            .where(*conditions)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
        )
        if paginate:
            query = query.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(query)).all()
        return [(row[0], row[1], row[2]) for row in rows], int(summary[0]), Decimal(summary[1])

    async def list_invoices(
        self,
        *,
        page: int,
        page_size: int,
        member: str | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        plan: str | None,
        tier: str | None,
        paginate: bool = True,
    ) -> tuple[list[tuple[Invoice, User]], int, Decimal]:
        conditions = self._conditions(
            member=member,
            status=status,
            date_from=date_from,
            date_to=date_to,
            plan=plan,
            tier=tier,
        )
        base = (
            Invoice.__table__
            .join(User, User.id == Invoice.user_id)
            .join(Payment, Payment.id == Invoice.payment_id)
            .join(MembershipPlan, MembershipPlan.id == Payment.plan_id)
        )
        summary = (
            await self.session.execute(
                select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0))
                .select_from(base)
                .where(*conditions),
            )
        ).one()
        query = (
            select(Invoice, User)
            .select_from(base)
            .where(*conditions)
            .order_by(Invoice.transaction_date.desc(), Invoice.id.desc())
        )
        if paginate:
            query = query.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(query)).all()
        return [(row[0], row[1]) for row in rows], int(summary[0]), Decimal(summary[1])


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_preferences(self, user_id: UUID) -> NotificationPreference | None:
        return (
            await self.session.execute(
                select(NotificationPreference).where(NotificationPreference.user_id == user_id),
            )
        ).scalar_one_or_none()

    async def get_or_create_preferences(self, user_id: UUID) -> NotificationPreference:
        preferences = await self.get_preferences(user_id)
        if preferences:
            return preferences
        preferences = NotificationPreference(user_id=user_id)
        self.session.add(preferences)
        await self.session.flush()
        return preferences

    async def list_notifications(self, user_id: UUID, page: int, page_size: int) -> tuple[list[Notification], int, int]:
        conditions = (Notification.user_id == user_id, Notification.channel == "in_app")
        total = int((await self.session.execute(select(func.count(Notification.id)).where(*conditions))).scalar_one())
        unread = int(
            (
                await self.session.execute(
                    select(func.count(Notification.id)).where(*conditions, Notification.read_at.is_(None)),
                )
            ).scalar_one(),
        )
        items = list(
            (
                await self.session.execute(
                    select(Notification)
                    .where(*conditions)
                    .order_by(Notification.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size),
                )
            ).scalars().all(),
        )
        return items, total, unread

    async def get_notification_for_user(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        return (
            await self.session.execute(
                select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id),
            )
        ).scalar_one_or_none()

    async def mark_all_read(self, user_id: UUID, read_at: datetime) -> int:
        items = list(
            (
                await self.session.execute(
                    select(Notification).where(
                        Notification.user_id == user_id,
                        Notification.channel == "in_app",
                        Notification.read_at.is_(None),
                    ),
                )
            ).scalars().all(),
        )
        for item in items:
            item.read_at = read_at
        return len(items)

    async def create_notification(self, **values: Any) -> Notification:
        item = Notification(**values)
        self.session.add(item)
        await self.session.flush()
        return item

    async def notification_exists(self, dedupe_key: str) -> bool:
        return bool(
            (
                await self.session.execute(
                    select(func.count(Notification.id)).where(Notification.dedupe_key == dedupe_key),
                )
            ).scalar_one(),
        )

    async def reminder_candidates(self, expiry_date: date) -> list[tuple[UserMembership, User]]:
        rows = (
            await self.session.execute(
                select(UserMembership, User)
                .join(User, User.id == UserMembership.user_id)
                .where(
                    UserMembership.expiry_date == expiry_date,
                    UserMembership.status.in_(("active", "expiring_soon")),
                    User.is_email_verified.is_(True),
                ),
            )
        ).all()
        return [(row[0], row[1]) for row in rows]

    async def create_broadcast(self, **values: Any) -> BroadcastAnnouncement:
        item = BroadcastAnnouncement(**values)
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_broadcast(self, broadcast_id: UUID) -> BroadcastAnnouncement | None:
        return await self.session.get(BroadcastAnnouncement, broadcast_id)

    async def list_broadcasts(self) -> list[BroadcastAnnouncement]:
        return list(
            (
                await self.session.execute(
                    select(BroadcastAnnouncement).order_by(BroadcastAnnouncement.created_at.desc()),
                )
            ).scalars().all(),
        )

    async def list_active_broadcasts(self, *, now: datetime, tier: str) -> list[BroadcastAnnouncement]:
        return list(
            (
                await self.session.execute(
                    select(BroadcastAnnouncement)
                    .where(
                        BroadcastAnnouncement.is_active.is_(True),
                        BroadcastAnnouncement.starts_at <= now,
                        or_(BroadcastAnnouncement.ends_at.is_(None), BroadcastAnnouncement.ends_at > now),
                        BroadcastAnnouncement.audience.in_(("all", "members", tier)),
                    )
                    .order_by(BroadcastAnnouncement.starts_at.desc()),
                )
            ).scalars().all(),
        )


class ConfigurationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> SystemConfiguration | None:
        return (
            await self.session.execute(
                select(SystemConfiguration).where(SystemConfiguration.key == key),
            )
        ).scalar_one_or_none()

    async def list_keys(self, keys: tuple[str, ...]) -> list[SystemConfiguration]:
        return list(
            (
                await self.session.execute(
                    select(SystemConfiguration)
                    .where(SystemConfiguration.key.in_(keys))
                    .order_by(SystemConfiguration.key),
                )
            ).scalars().all(),
        )
