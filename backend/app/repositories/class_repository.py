from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.classes import ClassBooking, ClassWaitlist, GymClass, PersonalTrainer
from app.models.user import User


class ClassRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_trainers(self, *, active: bool | None = True) -> list[PersonalTrainer]:
        query = select(PersonalTrainer)
        if active is not None:
            query = query.where(PersonalTrainer.is_active.is_(active))
        return list((await self.session.execute(query.order_by(PersonalTrainer.display_name))).scalars().all())

    async def get_trainer(self, trainer_id: UUID, *, for_update: bool = False) -> PersonalTrainer | None:
        query = select(PersonalTrainer).where(PersonalTrainer.id == trainer_id)
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_trainer_by_user(self, user_id: UUID) -> PersonalTrainer | None:
        return (
            await self.session.execute(select(PersonalTrainer).where(PersonalTrainer.user_id == user_id))
        ).scalar_one_or_none()

    async def create_trainer(self, **values) -> PersonalTrainer:
        item = PersonalTrainer(**values)
        self.session.add(item)
        await self.session.flush()
        return item

    async def upcoming_for_trainers(self, trainer_ids: list[UUID]) -> list[GymClass]:
        if not trainer_ids:
            return []
        return list(
            (
                await self.session.execute(
                    select(GymClass)
                    .where(
                        GymClass.trainer_id.in_(trainer_ids),
                        GymClass.status == "scheduled",
                        GymClass.start_at > func.now(),
                    )
                    .order_by(GymClass.start_at, GymClass.id),
                )
            ).scalars().all(),
        )

    async def upcoming_for_trainer(self, trainer_id: UUID) -> list[GymClass]:
        return await self.upcoming_for_trainers([trainer_id])

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

    async def member_classes(
        self,
        *,
        user_id: UUID,
        class_id: UUID | None = None,
        class_ids: list[UUID] | None = None,
        upcoming_only: bool = True,
    ) -> list[tuple[GymClass, PersonalTrainer | None, int, UUID | None, str | None, str | None, int | None]]:
        member_booking = aliased(ClassBooking)
        member_waitlist = aliased(ClassWaitlist)
        booking_count = (
            select(func.count(ClassBooking.id))
            .where(ClassBooking.class_id == GymClass.id, ClassBooking.status == "booked")
            .correlate(GymClass)
            .scalar_subquery()
        )
        query = (
            select(
                GymClass,
                PersonalTrainer,
                booking_count,
                member_booking.id,
                member_booking.status,
                member_waitlist.status,
                member_waitlist.position,
            )
            .outerjoin(PersonalTrainer, PersonalTrainer.id == GymClass.trainer_id)
            .outerjoin(
                member_booking,
                (member_booking.class_id == GymClass.id) & (member_booking.user_id == user_id),
            )
            .outerjoin(
                member_waitlist,
                (member_waitlist.class_id == GymClass.id) & (member_waitlist.user_id == user_id),
            )
        )
        if class_id:
            query = query.where(GymClass.id == class_id)
        if class_ids is not None:
            if not class_ids:
                return []
            query = query.where(GymClass.id.in_(class_ids))
        if upcoming_only:
            query = query.where(GymClass.start_at > func.now())
        rows = (await self.session.execute(query.order_by(GymClass.start_at, GymClass.id))).all()
        return [(row[0], row[1], int(row[2]), row[3], row[4], row[5], row[6]) for row in rows]

    async def get_booking_for_user(
        self,
        *,
        class_id: UUID,
        user_id: UUID,
        for_update: bool = False,
    ) -> ClassBooking | None:
        query = select(ClassBooking).where(ClassBooking.class_id == class_id, ClassBooking.user_id == user_id)
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_waitlist_for_user(
        self,
        *,
        class_id: UUID,
        user_id: UUID,
        for_update: bool = False,
    ) -> ClassWaitlist | None:
        query = select(ClassWaitlist).where(ClassWaitlist.class_id == class_id, ClassWaitlist.user_id == user_id)
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def confirmed_booking_count(self, class_id: UUID) -> int:
        return int(
            (
                await self.session.execute(
                    select(func.count(ClassBooking.id)).where(
                        ClassBooking.class_id == class_id,
                        ClassBooking.status == "booked",
                    ),
                )
            ).scalar_one(),
        )

    async def create_booking(self, *, class_id: UUID, user_id: UUID) -> ClassBooking:
        item = ClassBooking(class_id=class_id, user_id=user_id, status="booked")
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_booking(self, booking_id: UUID, *, for_update: bool = False) -> ClassBooking | None:
        query = select(ClassBooking).where(ClassBooking.id == booking_id)
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def list_bookings_for_user(self, user_id: UUID, *, limit: int = 100) -> list[ClassBooking]:
        return list(
            (
                await self.session.execute(
                    select(ClassBooking)
                    .join(GymClass, GymClass.id == ClassBooking.class_id)
                    .where(ClassBooking.user_id == user_id)
                    .order_by(GymClass.start_at.desc(), ClassBooking.created_at.desc())
                    .limit(limit),
                )
            ).scalars().all(),
        )

    async def list_waitlists_for_user(self, user_id: UUID, *, limit: int = 100) -> list[ClassWaitlist]:
        return list(
            (
                await self.session.execute(
                    select(ClassWaitlist)
                    .join(GymClass, GymClass.id == ClassWaitlist.class_id)
                    .where(ClassWaitlist.user_id == user_id)
                    .order_by(GymClass.start_at.desc(), ClassWaitlist.created_at.desc())
                    .limit(limit),
                )
            ).scalars().all(),
        )

    async def active_waitlist_count(self, class_id: UUID) -> int:
        return int(
            (
                await self.session.execute(
                    select(func.count(ClassWaitlist.id)).where(
                        ClassWaitlist.class_id == class_id,
                        ClassWaitlist.status == "waiting",
                    ),
                )
            ).scalar_one(),
        )

    async def next_waitlist_position(self, class_id: UUID) -> int:
        maximum = (
            await self.session.execute(
                select(func.max(ClassWaitlist.position)).where(ClassWaitlist.class_id == class_id),
            )
        ).scalar_one()
        return int(maximum or 0) + 1

    async def create_waitlist(self, *, class_id: UUID, user_id: UUID, position: int) -> ClassWaitlist:
        item = ClassWaitlist(class_id=class_id, user_id=user_id, position=position, status="waiting")
        self.session.add(item)
        await self.session.flush()
        return item

    async def waiting_entries_for_update(self, class_id: UUID) -> list[tuple[ClassWaitlist, User]]:
        rows = (
            await self.session.execute(
                select(ClassWaitlist, User)
                .join(User, User.id == ClassWaitlist.user_id)
                .where(ClassWaitlist.class_id == class_id, ClassWaitlist.status == "waiting")
                .order_by(ClassWaitlist.position, ClassWaitlist.created_at, ClassWaitlist.id)
                .with_for_update(),
            )
        ).all()
        return [(row[0], row[1]) for row in rows]
