from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.exceptions import AppError, ConflictError, ResourceNotFoundError
from app.models.classes import ClassBooking, ClassWaitlist, GymClass, PersonalTrainer
from app.models.user import User
from app.repositories.class_repository import ClassRepository
from app.repositories.operations_repository import AuditRepository
from app.schemas.class_schema import (
    ClassCancel,
    ClassCreate,
    ClassItem,
    ClassPage,
    ClassUpdate,
    BookingItem,
    MemberClassItem,
    MemberClassList,
    MemberBookings,
    TrainerAdminItem,
    TrainerClassSummary,
    TrainerCreate,
    TrainerItem,
    TrainerUpdate,
    WaitlistItem,
)
from app.schemas.operations_schema import PageInfo
from app.services.configuration_service import ConfigurationService
from app.services.lifecycle_service import MembershipLifecycleService
from app.services.notification_service import NotificationService


def validate_class_times(start_at: datetime, end_at: datetime, *, allow_past: bool = False) -> None:
    if start_at.tzinfo is None or end_at.tzinfo is None:
        raise AppError("CLASS_TIMEZONE_REQUIRED", "Class times must include a timezone.", 422)
    if end_at <= start_at:
        raise AppError("CLASS_TIME_INVALID", "Class end time must be after its start time.", 422)
    if not allow_past and start_at <= datetime.now(UTC):
        raise AppError("CLASS_START_IN_PAST", "New or rescheduled classes must start in the future.", 422)


class ClassService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.classes = ClassRepository(session)
        self.audit = AuditRepository(session)

    async def list_trainers(self) -> list[TrainerItem]:
        trainers = await self.classes.list_trainers()
        upcoming = await self.classes.upcoming_for_trainers([item.id for item in trainers])
        by_trainer = TrainerService.group_classes(upcoming)
        return [TrainerService.public_item(item, by_trainer.get(item.id, [])) for item in trainers]

    async def list_classes(self, **filters) -> ClassPage:
        rows, total, scheduled, cancelled = await self.classes.list_classes(**filters)
        return ClassPage(
            items=[self._item(item, trainer_name) for item, trainer_name in rows],
            page=PageInfo(
                page=filters["page"],
                page_size=filters["page_size"],
                total=total,
                pages=ceil(total / filters["page_size"]) if total else 0,
            ),
            scheduled_count=scheduled,
            cancelled_count=cancelled,
        )

    async def create(self, *, actor: User, payload: ClassCreate) -> ClassItem:
        validate_class_times(payload.start_at, payload.end_at)
        trainer_name = await self._trainer_name(payload.trainer_id)
        await self._ensure_no_overlap(
            start_at=payload.start_at,
            end_at=payload.end_at,
            location=payload.location,
            trainer_id=payload.trainer_id,
        )
        item = await self.classes.create_class(**payload.model_dump(), status="scheduled")
        await self.audit.create(
            actor_user_id=actor.id,
            action="class.created",
            entity_type="class",
            entity_id=str(item.id),
            reason="Class schedule creation",
            outcome="scheduled",
            summary=f"Class '{item.title}' was scheduled.",
            after_data=self._audit_data(item),
        )
        await self.session.commit()
        await self.session.refresh(item)
        return self._item(item, trainer_name)

    async def update(self, *, class_id: UUID, actor: User, payload: ClassUpdate) -> ClassItem:
        item = await self.classes.get_class(class_id, for_update=True)
        if not item:
            raise ResourceNotFoundError("Class was not found.")
        if item.status != "scheduled":
            raise ConflictError("Only scheduled classes can be edited.")
        before = self._audit_data(item)
        changes = payload.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(item, key, value)
        validate_class_times(item.start_at, item.end_at)
        trainer_name = await self._trainer_name(item.trainer_id)
        await self._ensure_no_overlap(
            start_at=item.start_at,
            end_at=item.end_at,
            location=item.location,
            trainer_id=item.trainer_id,
            exclude_id=item.id,
        )
        await self.audit.create(
            actor_user_id=actor.id,
            action="class.updated",
            entity_type="class",
            entity_id=str(item.id),
            reason="Class schedule update",
            outcome="scheduled",
            summary=f"Class '{item.title}' was updated.",
            before_data=before,
            after_data=self._audit_data(item),
        )
        await self.session.commit()
        await self.session.refresh(item)
        return self._item(item, trainer_name)

    async def cancel(self, *, class_id: UUID, actor: User, payload: ClassCancel) -> ClassItem:
        item = await self.classes.get_class(class_id, for_update=True)
        if not item:
            raise ResourceNotFoundError("Class was not found.")
        trainer_name = await self._trainer_name(item.trainer_id, require_active=False)
        if item.status == "cancelled":
            return self._item(item, trainer_name)
        if item.status != "scheduled":
            raise ConflictError("Only scheduled classes can be cancelled.")
        before = self._audit_data(item)
        item.status = "cancelled"
        item.cancellation_reason = payload.reason.strip()
        item.cancelled_by_id = actor.id
        item.cancelled_at = datetime.now(UTC)
        await self.audit.create(
            actor_user_id=actor.id,
            action="class.cancelled",
            entity_type="class",
            entity_id=str(item.id),
            reason=item.cancellation_reason,
            outcome="cancelled",
            summary=f"Class '{item.title}' was cancelled.",
            before_data=before,
            after_data=self._audit_data(item),
        )
        await self.session.commit()
        await self.session.refresh(item)
        return self._item(item, trainer_name)

    async def _trainer_name(self, trainer_id: UUID | None, *, require_active: bool = True) -> str | None:
        if not trainer_id:
            return None
        trainer = await self.classes.get_trainer(trainer_id)
        if not trainer or (require_active and not trainer.is_active):
            raise AppError("TRAINER_UNAVAILABLE", "The selected trainer is unavailable.", 422)
        return trainer.display_name

    async def _ensure_no_overlap(self, **values) -> None:
        conflict = await self.classes.find_overlap(**values)
        if conflict:
            raise ConflictError(
                "The trainer or location is already assigned to an overlapping class.",
                {"conflicting_class_id": str(conflict.id), "conflicting_title": conflict.title},
            )

    @staticmethod
    def _item(item: GymClass, trainer_name: str | None) -> ClassItem:
        return ClassItem(
            id=item.id,
            title=item.title,
            class_type=item.class_type,
            description=item.description,
            start_at=item.start_at,
            end_at=item.end_at,
            capacity=item.capacity,
            status=item.status,
            trainer_id=item.trainer_id,
            trainer_name=trainer_name,
            location=item.location,
            cancellation_reason=item.cancellation_reason,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def _audit_data(item: GymClass) -> dict[str, object]:
        return {
            "title": item.title,
            "class_type": item.class_type,
            "start_at": item.start_at.isoformat(),
            "end_at": item.end_at.isoformat(),
            "capacity": item.capacity,
            "trainer_id": str(item.trainer_id) if item.trainer_id else None,
            "location": item.location,
            "status": item.status,
        }


class TrainerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.trainers = ClassRepository(session)
        self.audit = AuditRepository(session)

    async def list_public(self) -> list[TrainerItem]:
        trainers = await self.trainers.list_trainers()
        upcoming = await self.trainers.upcoming_for_trainers([item.id for item in trainers])
        by_trainer = self.group_classes(upcoming)
        return [self.public_item(item, by_trainer.get(item.id, [])) for item in trainers]

    async def get_public(self, trainer_id: UUID) -> TrainerItem:
        trainer = await self.trainers.get_trainer(trainer_id)
        if not trainer or not trainer.is_active:
            raise ResourceNotFoundError("Trainer was not found.")
        return self.public_item(trainer, await self.trainers.upcoming_for_trainer(trainer.id))

    async def get_own(self, user: User) -> TrainerItem:
        trainer = await self.trainers.get_trainer_by_user(user.id)
        if not trainer:
            raise ResourceNotFoundError("Your trainer profile has not been linked. Contact a manager.")
        return self.public_item(trainer, await self.trainers.upcoming_for_trainer(trainer.id))

    async def list_admin(self, *, active: bool | None) -> list[TrainerAdminItem]:
        trainers = await self.trainers.list_trainers(active=active)
        upcoming = await self.trainers.upcoming_for_trainers([item.id for item in trainers])
        by_trainer = self.group_classes(upcoming)
        return [self.admin_item(item, by_trainer.get(item.id, [])) for item in trainers]

    async def create(self, *, actor: User, payload: TrainerCreate) -> TrainerAdminItem:
        await self._validate_user_link(payload.user_id)
        trainer = await self.trainers.create_trainer(**payload.model_dump(), is_active=True)
        await self.audit.create(
            actor_user_id=actor.id,
            action="trainer.created",
            entity_type="personal_trainer",
            entity_id=str(trainer.id),
            reason="Trainer profile creation",
            outcome="active",
            summary=f"Trainer profile '{trainer.display_name}' was created.",
            after_data=self._audit_data(trainer),
        )
        await self.session.commit()
        await self.session.refresh(trainer)
        return self.admin_item(trainer, [])

    async def update(
        self,
        *,
        trainer_id: UUID,
        actor: User,
        payload: TrainerUpdate,
    ) -> TrainerAdminItem:
        trainer = await self.trainers.get_trainer(trainer_id, for_update=True)
        if not trainer:
            raise ResourceNotFoundError("Trainer was not found.")
        before = self._audit_data(trainer)
        changes = payload.model_dump(exclude_unset=True)
        if "user_id" in changes and changes["user_id"] != trainer.user_id:
            await self._validate_user_link(changes["user_id"], trainer_id=trainer.id)
        for key, value in changes.items():
            setattr(trainer, key, value)
        await self.audit.create(
            actor_user_id=actor.id,
            action="trainer.updated",
            entity_type="personal_trainer",
            entity_id=str(trainer.id),
            reason="Trainer profile update",
            outcome="active" if trainer.is_active else "inactive",
            summary=f"Trainer profile '{trainer.display_name}' was updated.",
            before_data=before,
            after_data=self._audit_data(trainer),
        )
        await self.session.commit()
        await self.session.refresh(trainer)
        return self.admin_item(trainer, await self.trainers.upcoming_for_trainer(trainer.id))

    async def deactivate(self, *, trainer_id: UUID, actor: User) -> TrainerAdminItem:
        trainer = await self.trainers.get_trainer(trainer_id, for_update=True)
        if not trainer:
            raise ResourceNotFoundError("Trainer was not found.")
        upcoming = await self.trainers.upcoming_for_trainer(trainer.id)
        if upcoming:
            raise ConflictError(
                "Reassign or unassign the trainer's future classes before deactivation.",
                {"upcoming_class_ids": [str(item.id) for item in upcoming]},
            )
        if trainer.is_active:
            trainer.is_active = False
            await self.audit.create(
                actor_user_id=actor.id,
                action="trainer.deactivated",
                entity_type="personal_trainer",
                entity_id=str(trainer.id),
                reason="Trainer profile deactivation",
                outcome="inactive",
                summary=f"Trainer profile '{trainer.display_name}' was deactivated.",
                before_data={**self._audit_data(trainer), "is_active": True},
                after_data=self._audit_data(trainer),
            )
            await self.session.commit()
            await self.session.refresh(trainer)
        return self.admin_item(trainer, [])

    async def _validate_user_link(self, user_id: UUID | None, *, trainer_id: UUID | None = None) -> None:
        if user_id is None:
            return
        user = await self.session.get(User, user_id)
        if not user or user.role != "pt":
            raise AppError("TRAINER_USER_INVALID", "A trainer profile can only link to a PT user.", 422)
        existing = await self.trainers.get_trainer_by_user(user_id)
        if existing and existing.id != trainer_id:
            raise ConflictError("That PT user already has a trainer profile.")

    @staticmethod
    def group_classes(items: list[GymClass]) -> dict[UUID, list[GymClass]]:
        grouped: dict[UUID, list[GymClass]] = {}
        for item in items:
            if item.trainer_id:
                grouped.setdefault(item.trainer_id, []).append(item)
        return grouped

    @staticmethod
    def public_item(trainer, upcoming: list[GymClass]) -> TrainerItem:
        return TrainerItem(
            id=trainer.id,
            display_name=trainer.display_name,
            bio=trainer.bio,
            specialty=trainer.specialty,
            availability_summary=trainer.availability_summary,
            is_active=trainer.is_active,
            upcoming_classes=[
                TrainerClassSummary(
                    id=item.id,
                    title=item.title,
                    class_type=item.class_type,
                    start_at=item.start_at,
                    end_at=item.end_at,
                    location=item.location,
                )
                for item in upcoming[:3]
            ],
        )

    @classmethod
    def admin_item(cls, trainer, upcoming: list[GymClass]) -> TrainerAdminItem:
        public = cls.public_item(trainer, upcoming)
        return TrainerAdminItem(
            **public.model_dump(),
            user_id=trainer.user_id,
            created_at=trainer.created_at,
            updated_at=trainer.updated_at,
        )

    @staticmethod
    def _audit_data(trainer) -> dict[str, object]:
        return {
            "display_name": trainer.display_name,
            "specialty": trainer.specialty,
            "availability_summary": trainer.availability_summary,
            "is_active": trainer.is_active,
            "user_id": str(trainer.user_id) if trainer.user_id else None,
        }


def class_cancellation_cutoff(start_at: datetime, window_hours: int) -> datetime:
    return start_at - timedelta(hours=window_hours)


def can_cancel_class_booking(*, now: datetime, start_at: datetime, window_hours: int) -> bool:
    return now <= class_cancellation_cutoff(start_at, window_hours)


class BookingService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.classes = ClassRepository(session)
        self.lifecycle = MembershipLifecycleService(session)
        self.configuration = ConfigurationService(session, redis)
        self.notifications = NotificationService(session)

    async def list_upcoming(self, user: User) -> MemberClassList:
        _, status, eligible, reason = await self.lifecycle.access_snapshot(user)
        rows = await self.classes.member_classes(user_id=user.id)
        return MemberClassList(
            items=[self._member_class(row, eligible=eligible) for row in rows],
            booking_eligible=eligible,
            eligibility_status=status,
            eligibility_reason=reason,
        )

    async def get_member_class(self, *, class_id: UUID, user: User) -> MemberClassItem:
        _, _, eligible, _ = await self.lifecycle.access_snapshot(user)
        rows = await self.classes.member_classes(user_id=user.id, class_id=class_id, upcoming_only=False)
        if not rows:
            raise ResourceNotFoundError("Class was not found.")
        return self._member_class(rows[0], eligible=eligible)

    async def book(self, *, class_id: UUID, user: User) -> BookingItem:
        await self.lifecycle.require_eligible_membership(user)
        gym_class = await self.classes.get_class(class_id, for_update=True)
        if not gym_class:
            raise ResourceNotFoundError("Class was not found.")
        if gym_class.status != "scheduled":
            raise AppError("CLASS_UNAVAILABLE", "Only scheduled classes can be booked.", 409)
        if gym_class.start_at <= datetime.now(UTC):
            raise AppError("CLASS_ALREADY_STARTED", "A class cannot be booked after it starts.", 409)
        booking = await self.classes.get_booking_for_user(
            class_id=class_id,
            user_id=user.id,
            for_update=True,
        )
        if booking and booking.status == "booked":
            raise AppError("BOOKING_EXISTS", "You already booked this class.", 409)
        waitlist = await self.classes.get_waitlist_for_user(
            class_id=class_id,
            user_id=user.id,
            for_update=True,
        )
        if waitlist and waitlist.status == "waiting":
            raise AppError("WAITLIST_EXISTS", "Leave the waitlist before booking this class.", 409)
        if await self.classes.confirmed_booking_count(class_id) >= gym_class.capacity:
            raise AppError("CLASS_FULL", "This class is full. Join the waitlist instead.", 409)
        if booking:
            booking.status = "booked"
            await self.session.flush()
        else:
            booking = await self.classes.create_booking(class_id=class_id, user_id=user.id)
        await self.session.commit()
        await self.session.refresh(booking)
        return await self._booking_item(
            booking=booking,
            gym_class=await self.get_member_class(class_id=class_id, user=user),
        )

    async def list_my(self, user: User) -> MemberBookings:
        bookings = await self.classes.list_bookings_for_user(user.id)
        waitlists = await self.classes.list_waitlists_for_user(user.id)
        class_ids = list({item.class_id for item in [*bookings, *waitlists]})
        _, _, eligible, _ = await self.lifecycle.access_snapshot(user)
        rows = await self.classes.member_classes(
            user_id=user.id,
            class_ids=class_ids,
            upcoming_only=False,
        )
        classes = {row[0].id: self._member_class(row, eligible=eligible) for row in rows}
        window = await self.configuration.get_int("class_cancellation_window_hours")
        return MemberBookings(
            bookings=[self._booking_item_with_window(item, classes[item.class_id], window) for item in bookings],
            waitlists=[
                WaitlistItem(
                    id=item.id,
                    status=item.status,
                    position=item.position,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    gym_class=classes[item.class_id],
                )
                for item in waitlists
            ],
            cancellation_window_hours=window,
        )

    async def join_waitlist(self, *, class_id: UUID, user: User) -> WaitlistItem:
        await self.lifecycle.require_eligible_membership(user)
        gym_class = await self.classes.get_class(class_id, for_update=True)
        if not gym_class:
            raise ResourceNotFoundError("Class was not found.")
        if gym_class.status != "scheduled" or gym_class.start_at <= datetime.now(UTC):
            raise AppError("CLASS_UNAVAILABLE", "Only future scheduled classes accept a waitlist.", 409)
        booking = await self.classes.get_booking_for_user(class_id=class_id, user_id=user.id, for_update=True)
        if booking and booking.status == "booked":
            raise AppError("BOOKING_EXISTS", "You already booked this class.", 409)
        waitlist = await self.classes.get_waitlist_for_user(class_id=class_id, user_id=user.id, for_update=True)
        if waitlist and waitlist.status == "waiting":
            raise AppError("WAITLIST_EXISTS", "You are already on this waitlist.", 409)
        if await self.classes.confirmed_booking_count(class_id) < gym_class.capacity:
            raise AppError("WAITLIST_NOT_REQUIRED", "This class still has an available place.", 409)
        limit = await self.configuration.get_int("waitlist_size")
        if limit == 0 or await self.classes.active_waitlist_count(class_id) >= limit:
            raise AppError("WAITLIST_FULL", "The waitlist is full.", 409)
        position = await self.classes.next_waitlist_position(class_id)
        if waitlist:
            waitlist.status = "waiting"
            waitlist.position = position
            await self.session.flush()
        else:
            waitlist = await self.classes.create_waitlist(class_id=class_id, user_id=user.id, position=position)
        await self.session.commit()
        await self.session.refresh(waitlist)
        return WaitlistItem(
            id=waitlist.id,
            status=waitlist.status,
            position=waitlist.position,
            created_at=waitlist.created_at,
            updated_at=waitlist.updated_at,
            gym_class=await self.get_member_class(class_id=class_id, user=user),
        )

    async def leave_waitlist(self, *, class_id: UUID, user: User) -> WaitlistItem:
        gym_class = await self.classes.get_class(class_id, for_update=True)
        if not gym_class:
            raise ResourceNotFoundError("Class was not found.")
        waitlist = await self.classes.get_waitlist_for_user(class_id=class_id, user_id=user.id, for_update=True)
        if not waitlist:
            raise ResourceNotFoundError("Waitlist entry was not found.")
        if waitlist.status == "promoted":
            raise AppError("WAITLIST_PROMOTED", "This waitlist entry has already been promoted to a booking.", 409)
        if waitlist.status == "waiting":
            waitlist.status = "cancelled"
            await self.session.commit()
            await self.session.refresh(waitlist)
        return WaitlistItem(
            id=waitlist.id,
            status=waitlist.status,
            position=waitlist.position,
            created_at=waitlist.created_at,
            updated_at=waitlist.updated_at,
            gym_class=await self.get_member_class(class_id=class_id, user=user),
        )

    async def cancel(self, *, booking_id: UUID, user: User) -> BookingItem:
        current = await self.classes.get_booking(booking_id)
        if not current or current.user_id != user.id:
            raise ResourceNotFoundError("Booking was not found.")
        gym_class = await self.classes.get_class(current.class_id, for_update=True)
        if not gym_class:
            raise ResourceNotFoundError("Class was not found.")
        booking = await self.classes.get_booking(booking_id, for_update=True)
        if not booking or booking.user_id != user.id:
            raise ResourceNotFoundError("Booking was not found.")
        if booking.status == "cancelled":
            return await self._booking_item(
                booking=booking,
                gym_class=await self.get_member_class(class_id=gym_class.id, user=user),
            )
        if gym_class.status != "scheduled":
            raise AppError("CLASS_UNAVAILABLE", "Bookings for this class cannot be cancelled.", 409)
        now = datetime.now(UTC)
        if gym_class.start_at <= now:
            raise AppError("CLASS_ALREADY_STARTED", "A booking cannot be cancelled after class starts.", 409)
        window = await self.configuration.get_int("class_cancellation_window_hours")
        if not can_cancel_class_booking(now=now, start_at=gym_class.start_at, window_hours=window):
            raise AppError(
                "LATE_CANCELLATION",
                f"Cancellation closes {window} hours before class starts.",
                409,
                {"cancellation_cutoff": class_cancellation_cutoff(gym_class.start_at, window).isoformat()},
            )
        booking.status = "cancelled"
        await self.session.flush()
        await self._promote(gym_class)
        await self.session.commit()
        await self.session.refresh(booking)
        return await self._booking_item(
            booking=booking,
            gym_class=await self.get_member_class(class_id=gym_class.id, user=user),
            window=window,
        )

    async def _promote(self, gym_class: GymClass) -> ClassBooking | None:
        if await self.classes.confirmed_booking_count(gym_class.id) >= gym_class.capacity:
            return None
        for waitlist, user in await self.classes.waiting_entries_for_update(gym_class.id):
            try:
                await self.lifecycle.require_eligible_membership(user)
            except AppError as exc:
                if exc.code not in {"MEMBERSHIP_REQUIRED", "MEMBERSHIP_INELIGIBLE"}:
                    raise
                waitlist.status = "cancelled"
                continue
            booking = await self.classes.get_booking_for_user(
                class_id=gym_class.id,
                user_id=user.id,
                for_update=True,
            )
            if booking and booking.status == "booked":
                waitlist.status = "cancelled"
                continue
            if booking:
                booking.status = "booked"
                await self.session.flush()
            else:
                booking = await self.classes.create_booking(class_id=gym_class.id, user_id=user.id)
            waitlist.status = "promoted"
            await self.notifications.queue_class_promotion(
                user=user,
                class_id=gym_class.id,
                class_title=gym_class.title,
                class_start=gym_class.start_at,
                waitlist_id=waitlist.id,
                waitlist_position=waitlist.position,
            )
            return booking
        return None

    async def _booking_item(
        self,
        *,
        booking: ClassBooking,
        gym_class: MemberClassItem,
        window: int | None = None,
    ) -> BookingItem:
        return self._booking_item_with_window(
            booking,
            gym_class,
            window if window is not None else await self.configuration.get_int("class_cancellation_window_hours"),
        )

    @staticmethod
    def _booking_item_with_window(
        booking: ClassBooking,
        gym_class: MemberClassItem,
        window: int,
    ) -> BookingItem:
        cutoff = class_cancellation_cutoff(gym_class.start_at, window)
        return BookingItem(
            id=booking.id,
            status=booking.status,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            cancellation_cutoff=cutoff,
            can_cancel=(
                booking.status == "booked"
                and gym_class.status == "scheduled"
                and gym_class.start_at > datetime.now(UTC)
                and datetime.now(UTC) <= cutoff
            ),
            gym_class=gym_class,
        )

    @staticmethod
    def _member_class(
        row: tuple[GymClass, PersonalTrainer | None, int, UUID | None, str | None, str | None, int | None],
        *,
        eligible: bool,
    ) -> MemberClassItem:
        gym_class, trainer, confirmed, booking_id, booking_status, waitlist_status, waitlist_position = row
        remaining = max(gym_class.capacity - confirmed, 0)
        if gym_class.status != "scheduled":
            state = "cancelled"
        elif booking_status == "booked":
            state = "booked"
        elif waitlist_status == "waiting":
            state = "waitlisted"
        elif not eligible:
            state = "ineligible"
        elif remaining == 0:
            state = "full"
        else:
            state = "available"
        return MemberClassItem(
            id=gym_class.id,
            title=gym_class.title,
            class_type=gym_class.class_type,
            description=gym_class.description,
            start_at=gym_class.start_at,
            end_at=gym_class.end_at,
            capacity=gym_class.capacity,
            status=gym_class.status,
            location=gym_class.location,
            confirmed_booking_count=confirmed,
            remaining_capacity=remaining,
            trainer=TrainerService.public_item(trainer, []) if trainer else None,
            member_booking_id=booking_id,
            member_booking_status=booking_status,
            member_waitlist_status=waitlist_status,
            waitlist_position=waitlist_position,
            member_state=state,
        )
