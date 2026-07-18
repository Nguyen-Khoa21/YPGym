import logging
from datetime import UTC, date, datetime, timedelta
from math import ceil
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ResourceNotFoundError
from app.models.user import User
from app.repositories.operations_repository import AuditRepository, NotificationRepository
from app.schemas.notification_schema import (
    BroadcastCreate,
    BroadcastItem,
    BroadcastUpdate,
    NotificationItem,
    NotificationPage,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from app.schemas.operations_schema import OperationMessage, PageInfo

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notifications = NotificationRepository(session)
        self.audit = AuditRepository(session)

    async def get_preferences(self, user: User) -> NotificationPreferenceResponse:
        preferences = await self.notifications.get_or_create_preferences(user.id)
        await self.session.commit()
        return NotificationPreferenceResponse.model_validate(preferences)

    async def update_preferences(
        self,
        *,
        user: User,
        payload: NotificationPreferenceUpdate,
    ) -> NotificationPreferenceResponse:
        preferences = await self.notifications.get_or_create_preferences(user.id)
        for key, value in payload.model_dump().items():
            setattr(preferences, key, value)
        await self.session.commit()
        await self.session.refresh(preferences)
        return NotificationPreferenceResponse.model_validate(preferences)

    async def list_notifications(self, *, user: User, page: int, page_size: int) -> NotificationPage:
        items, total, unread = await self.notifications.list_notifications(user.id, page, page_size)
        return NotificationPage(
            items=[NotificationItem.model_validate(item) for item in items],
            page=PageInfo(
                page=page,
                page_size=page_size,
                total=total,
                pages=ceil(total / page_size) if total else 0,
            ),
            unread_count=unread,
        )

    async def mark_read(self, *, user: User, notification_id: UUID) -> OperationMessage:
        item = await self.notifications.get_notification_for_user(notification_id, user.id)
        if not item:
            raise ResourceNotFoundError("Notification was not found.")
        if item.channel != "in_app":
            raise ResourceNotFoundError("Notification was not found.")
        if not item.read_at:
            item.read_at = datetime.now(UTC)
            await self.session.commit()
        return OperationMessage(message="Notification marked as read.", code="NOTIFICATION_READ")

    async def mark_all_read(self, *, user: User) -> OperationMessage:
        count = await self.notifications.mark_all_read(user.id, datetime.now(UTC))
        await self.session.commit()
        return OperationMessage(message=f"Marked {count} notifications as read.", code="NOTIFICATIONS_READ")

    async def create_broadcast(self, *, actor: User, payload: BroadcastCreate) -> BroadcastItem:
        broadcast = await self.notifications.create_broadcast(
            **payload.model_dump(),
            creator_id=actor.id,
            is_active=True,
        )
        await self.audit.create(
            actor_user_id=actor.id,
            action="broadcast.created",
            entity_type="broadcast_announcement",
            entity_id=str(broadcast.id),
            reason="Member communication",
            outcome="active",
            summary=f"Broadcast '{broadcast.title}' was created for {broadcast.audience}.",
        )
        await self.session.commit()
        await self.session.refresh(broadcast)
        return BroadcastItem.model_validate(broadcast)

    async def update_broadcast(
        self,
        *,
        broadcast_id: UUID,
        actor: User,
        payload: BroadcastUpdate,
    ) -> BroadcastItem:
        broadcast = await self.notifications.get_broadcast(broadcast_id)
        if not broadcast:
            raise ResourceNotFoundError("Broadcast was not found.")
        before = {
            "audience": broadcast.audience,
            "title": broadcast.title,
            "starts_at": broadcast.starts_at.isoformat(),
            "ends_at": broadcast.ends_at.isoformat() if broadcast.ends_at else None,
            "is_active": broadcast.is_active,
        }
        changes = payload.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(broadcast, key, value)
        if broadcast.ends_at and broadcast.ends_at <= broadcast.starts_at:
            raise AppError("BROADCAST_PERIOD_INVALID", "Broadcast end time must be after its start time.", 422)
        await self.audit.create(
            actor_user_id=actor.id,
            action="broadcast.updated",
            entity_type="broadcast_announcement",
            entity_id=str(broadcast.id),
            reason="Broadcast update or deactivation",
            outcome="active" if broadcast.is_active else "inactive",
            summary=f"Broadcast '{broadcast.title}' was updated.",
            before_data=before,
            after_data={
                "audience": broadcast.audience,
                "title": broadcast.title,
                "starts_at": broadcast.starts_at.isoformat(),
                "ends_at": broadcast.ends_at.isoformat() if broadcast.ends_at else None,
                "is_active": broadcast.is_active,
            },
        )
        await self.session.commit()
        await self.session.refresh(broadcast)
        return BroadcastItem.model_validate(broadcast)

    async def list_admin_broadcasts(self) -> list[BroadcastItem]:
        return [BroadcastItem.model_validate(item) for item in await self.notifications.list_broadcasts()]

    async def list_active_broadcasts(self, user: User) -> list[BroadcastItem]:
        preferences = await self.notifications.get_or_create_preferences(user.id)
        if not preferences.broadcasts_enabled or not preferences.in_app_enabled:
            await self.session.commit()
            return []
        items = await self.notifications.list_active_broadcasts(now=datetime.now(UTC), tier=user.tier)
        await self.session.commit()
        return [BroadcastItem.model_validate(item) for item in items]

    async def send_expiry_reminders(self, *, today: date | None = None) -> int:
        today = today or date.today()
        created = 0
        now = datetime.now(UTC)
        for days in (7, 3, 1):
            for membership, user in await self.notifications.reminder_candidates(today + timedelta(days=days)):
                preferences = await self.notifications.get_or_create_preferences(user.id)
                if not preferences.expiry_reminders_enabled:
                    continue
                title = f"Membership expires in {days} day{'s' if days != 1 else ''}"
                message = f"Your YPGym membership expires on {membership.expiry_date.isoformat()}. Renew to keep uninterrupted access."
                if preferences.in_app_enabled:
                    dedupe_key = f"expiry:{membership.id}:{membership.expiry_date}:{days}:in_app"
                    if not await self.notifications.notification_exists(dedupe_key):
                        await self.notifications.create_notification(
                            user_id=user.id,
                            category="membership",
                            notification_type="expiry_reminder",
                            title=title,
                            message=message,
                            channel="in_app",
                            delivery_state="delivered",
                            delivered_at=now,
                            dedupe_key=dedupe_key,
                        )
                        created += 1
                if preferences.email_enabled:
                    dedupe_key = f"expiry:{membership.id}:{membership.expiry_date}:{days}:email"
                    if not await self.notifications.notification_exists(dedupe_key):
                        await self.notifications.create_notification(
                            user_id=user.id,
                            category="membership",
                            notification_type="expiry_reminder",
                            title=title,
                            message=message,
                            channel="email",
                            delivery_state="delivered",
                            delivered_at=now,
                            dedupe_key=dedupe_key,
                        )
                        logger.info("development_expiry_email user_id=%s days=%s", user.id, days)
                        created += 1
        await self.session.commit()
        return created
