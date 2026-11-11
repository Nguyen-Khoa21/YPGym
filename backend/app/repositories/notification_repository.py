from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classes import ClassBooking, GymClass
from app.models.membership import UserMembership
from app.models.operations import BroadcastAnnouncement, Notification, NotificationPreference
from app.models.user import User


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

    async def list_recent_unread(self, user_id: UUID, limit: int) -> tuple[list[Notification], int]:
        conditions = (
            Notification.user_id == user_id,
            Notification.channel == "in_app",
            Notification.read_at.is_(None),
        )
        unread = int(
            (await self.session.execute(select(func.count(Notification.id)).where(*conditions))).scalar_one(),
        )
        items = list(
            (
                await self.session.execute(
                    select(Notification)
                    .where(*conditions)
                    .order_by(Notification.created_at.desc(), Notification.id.desc())
                    .limit(limit),
                )
            ).scalars().all(),
        )
        return items, unread

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

    async def create_notification_once(self, **values: Any) -> bool:
        statement = (
            insert(Notification)
            .values(**values)
            .on_conflict_do_nothing(constraint="uq_notifications_dedupe_key")
            .returning(Notification.id)
        )
        return (await self.session.execute(statement)).scalar_one_or_none() is not None

    async def notification_exists(self, dedupe_key: str) -> bool:
        return bool(
            (
                await self.session.execute(
                    select(func.count(Notification.id)).where(Notification.dedupe_key == dedupe_key),
                )
            ).scalar_one(),
        )

    async def next_auth_email_for_delivery(
        self,
        *,
        retry_before: datetime,
        max_attempts: int,
    ) -> tuple[Notification, User] | None:
        row = (
            await self.session.execute(
                select(Notification, User)
                .join(User, User.id == Notification.user_id)
                .where(
                    Notification.notification_type.in_((
                        "registration_welcome",
                        "oauth_provider_linked",
                        "oauth_provider_unlinked",
                        "oauth_account_created",
                    )),
                    Notification.channel == "email",
                    Notification.delivery_state == "pending",
                    Notification.delivery_attempts < max_attempts,
                    or_(
                        Notification.last_delivery_attempt_at.is_(None),
                        Notification.last_delivery_attempt_at <= retry_before,
                    ),
                )
                .order_by(Notification.created_at, Notification.id)
                .with_for_update(skip_locked=True)
                .limit(1),
            )
        ).first()
        return (row[0], row[1]) if row else None

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

    async def class_reminder_candidates(
        self,
        *,
        starts_after: datetime,
        starts_before: datetime,
    ) -> list[tuple[ClassBooking, GymClass, User, NotificationPreference | None]]:
        rows = (
            await self.session.execute(
                select(ClassBooking, GymClass, User, NotificationPreference)
                .join(GymClass, GymClass.id == ClassBooking.class_id)
                .join(User, User.id == ClassBooking.user_id)
                .outerjoin(NotificationPreference, NotificationPreference.user_id == User.id)
                .where(
                    ClassBooking.status == "confirmed",
                    GymClass.status == "scheduled",
                    GymClass.start_at > starts_after,
                    GymClass.start_at <= starts_before,
                )
                .order_by(GymClass.start_at, ClassBooking.id),
            )
        ).all()
        return [(row[0], row[1], row[2], row[3]) for row in rows]

    async def create_broadcast(self, **values: Any) -> BroadcastAnnouncement:
        item = BroadcastAnnouncement(**values)
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_broadcast(self, broadcast_id: UUID) -> BroadcastAnnouncement | None:
        return await self.session.get(BroadcastAnnouncement, broadcast_id)

    async def list_broadcasts(self, *, gym_id: UUID | None = None) -> list[BroadcastAnnouncement]:
        query = select(BroadcastAnnouncement)
        if gym_id is not None:
            query = query.where(BroadcastAnnouncement.gym_id == gym_id)
        return list(
            (
                await self.session.execute(
                    query.order_by(BroadcastAnnouncement.created_at.desc()),
                )
            ).scalars().all(),
        )

    async def list_active_broadcasts(
        self,
        *,
        now: datetime,
        tier: str,
        gym_id: UUID | None,
    ) -> list[BroadcastAnnouncement]:
        gym_scope = BroadcastAnnouncement.gym_id.is_(None)
        if gym_id is not None:
            gym_scope = or_(gym_scope, BroadcastAnnouncement.gym_id == gym_id)
        return list(
            (
                await self.session.execute(
                    select(BroadcastAnnouncement)
                    .where(
                        BroadcastAnnouncement.is_active.is_(True),
                        BroadcastAnnouncement.starts_at <= now,
                        or_(BroadcastAnnouncement.ends_at.is_(None), BroadcastAnnouncement.ends_at > now),
                        BroadcastAnnouncement.audience.in_(("all", "members", tier)),
                        gym_scope,
                    )
                    .order_by(BroadcastAnnouncement.starts_at.desc()),
                )
            ).scalars().all(),
        )
