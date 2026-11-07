from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Date, Integer, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceEvent, AttendanceSession, IoTDevice
from app.models.gym import DISTRICT_1_GYM_ID
from app.models.user import User


class AttendanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_device_for_update(self, device_id: str) -> IoTDevice | None:
        return (
            await self.session.execute(
                select(IoTDevice).where(IoTDevice.device_id == device_id).with_for_update(),
            )
        ).scalar_one_or_none()

    async def get_device(self, device_id: str) -> IoTDevice | None:
        return (
            await self.session.execute(
                select(IoTDevice).where(IoTDevice.device_id == device_id),
            )
        ).scalar_one_or_none()

    async def get_active_session(self, user_id: UUID, *, for_update: bool = False) -> AttendanceSession | None:
        query = select(AttendanceSession).where(
            AttendanceSession.user_id == user_id,
            AttendanceSession.status == "active",
        )
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_session(self, session_id: UUID, *, for_update: bool = False) -> AttendanceSession | None:
        query = select(AttendanceSession).where(AttendanceSession.id == session_id)
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def create_session(
        self,
        *,
        gym_id: UUID,
        user_id: UUID,
        checked_in_at: datetime,
        source: str,
        device_id: str | None,
    ) -> AttendanceSession:
        session = AttendanceSession(
            gym_id=gym_id,
            user_id=user_id,
            checked_in_at=checked_in_at,
            status="active",
            source=source,
            device_id=device_id,
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def create_event(
        self,
        *,
        attendance_session: AttendanceSession,
        event_type: str,
        event_at: datetime,
        source: str,
        device_id: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> AttendanceEvent:
        event = AttendanceEvent(
            gym_id=attendance_session.gym_id,
            session_id=attendance_session.id,
            user_id=attendance_session.user_id,
            event_type=event_type,
            event_at=event_at,
            source=source,
            device_id=device_id,
            event_metadata=metadata,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def active_count(self, *, gym_id: UUID) -> int:
        return int(
            (
                await self.session.execute(
                    select(func.count(AttendanceSession.id)).where(
                        AttendanceSession.gym_id == gym_id,
                        AttendanceSession.status == "active",
                    ),
                )
            ).scalar_one(),
        )

    async def timeout_candidates(self, cutoff: datetime) -> list[AttendanceSession]:
        return list(
            (
                await self.session.execute(
                    select(AttendanceSession)
                    .where(
                        AttendanceSession.status == "active",
                        AttendanceSession.checked_in_at <= cutoff,
                    )
                    .order_by(AttendanceSession.checked_in_at)
                    .with_for_update(skip_locked=True),
                )
            ).scalars().all(),
        )

    async def list_member_sessions(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[AttendanceSession], int, dict[UUID, list[AttendanceEvent]]]:
        total = int(
            (
                await self.session.execute(
                    select(func.count(AttendanceSession.id)).where(
                        AttendanceSession.user_id == user_id,
                        AttendanceSession.gym_id == gym_id,
                    ),
                )
            ).scalar_one(),
        )
        sessions = list(
            (
                await self.session.execute(
                    select(AttendanceSession)
                    .where(
                        AttendanceSession.user_id == user_id,
                        AttendanceSession.gym_id == gym_id,
                    )
                    .order_by(AttendanceSession.checked_in_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size),
                )
            ).scalars().all(),
        )
        return sessions, total, await self.events_for_sessions([item.id for item in sessions])

    async def distinct_member_visit_days(self, *, user_id: UUID, gym_id: UUID, gym_timezone: str) -> list[date]:
        local_day = cast(func.timezone(gym_timezone, AttendanceSession.checked_in_at), Date)
        return list(
            (
                await self.session.execute(
                    select(local_day)
                    .where(
                        AttendanceSession.user_id == user_id,
                        AttendanceSession.gym_id == gym_id,
                    )
                    .distinct()
                    .order_by(local_day.desc()),
                )
            ).scalars().all(),
        )

    async def count_distinct_qr_visit_days(
        self,
        *,
        user_id: UUID,
        gym_timezone: str,
        date_from: datetime,
        date_to: datetime,
    ) -> int:
        local_day = cast(func.timezone(gym_timezone, AttendanceSession.checked_in_at), Date)
        return int(
            (
                await self.session.execute(
                    select(func.count(func.distinct(local_day))).where(
                        AttendanceSession.user_id == user_id,
                        AttendanceSession.source == "iot_scanner",
                        AttendanceSession.checked_in_at >= date_from,
                        AttendanceSession.checked_in_at < date_to,
                    ),
                )
            ).scalar_one(),
        )

    async def list_admin_sessions(
        self,
        *,
        page: int,
        page_size: int,
        date_from: datetime | None,
        date_to: datetime | None,
        status: str | None,
        member: str | None,
        gym_id: UUID | None,
    ) -> tuple[list[tuple[AttendanceSession, User]], int, dict[UUID, list[AttendanceEvent]]]:
        conditions = []
        if date_from:
            conditions.append(AttendanceSession.checked_in_at >= date_from)
        if date_to:
            conditions.append(AttendanceSession.checked_in_at <= date_to)
        if status:
            conditions.append(AttendanceSession.status == status)
        if member:
            term = f"%{member.strip()}%"
            conditions.append(or_(User.name.ilike(term), User.email.ilike(term)))
        if gym_id:
            conditions.append(AttendanceSession.gym_id == gym_id)
        base = AttendanceSession.__table__.join(User, User.id == AttendanceSession.user_id)
        total = int(
            (
                await self.session.execute(
                    select(func.count(AttendanceSession.id)).select_from(base).where(*conditions),
                )
            ).scalar_one(),
        )
        rows = (
            await self.session.execute(
                select(AttendanceSession, User)
                .select_from(base)
                .where(*conditions)
                .order_by(AttendanceSession.checked_in_at.desc(), AttendanceSession.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size),
            )
        ).all()
        items = [(row[0], row[1]) for row in rows]
        return items, total, await self.events_for_sessions([item[0].id for item in items])

    async def events_for_sessions(self, session_ids: list[UUID]) -> dict[UUID, list[AttendanceEvent]]:
        if not session_ids:
            return {}
        events = list(
            (
                await self.session.execute(
                    select(AttendanceEvent)
                    .where(AttendanceEvent.session_id.in_(session_ids))
                    .order_by(AttendanceEvent.event_at),
                )
            ).scalars().all(),
        )
        grouped: dict[UUID, list[AttendanceEvent]] = {session_id: [] for session_id in session_ids}
        for event in events:
            grouped[event.session_id].append(event)
        return grouped

    async def peak_hours(
        self,
        *,
        date_from: datetime,
        date_to: datetime,
        gym_id: UUID = DISTRICT_1_GYM_ID,
    ) -> list[tuple[int, int, int]]:
        utc_event_at = func.timezone("UTC", AttendanceEvent.event_at)
        weekday = func.extract("dow", utc_event_at).cast(Integer)
        hour = func.extract("hour", utc_event_at).cast(Integer)
        rows = (
            await self.session.execute(
                select(weekday, hour, func.count(AttendanceEvent.id))
                .where(
                    AttendanceEvent.event_type == "check_in",
                    AttendanceEvent.gym_id == gym_id,
                    AttendanceEvent.event_at >= date_from,
                    AttendanceEvent.event_at <= date_to,
                )
                .group_by(weekday, hour)
                .order_by(weekday, hour),
            )
        ).all()
        return [(int(row[0]), int(row[1]), int(row[2])) for row in rows]

    async def visits_between(
        self,
        *,
        date_from: datetime,
        date_to: datetime,
        gym_id: UUID = DISTRICT_1_GYM_ID,
    ) -> int:
        return int(
            (
                await self.session.execute(
                    select(func.count(AttendanceEvent.id)).where(
                        AttendanceEvent.event_type == "check_in",
                        AttendanceEvent.gym_id == gym_id,
                        AttendanceEvent.event_at >= date_from,
                        AttendanceEvent.event_at <= date_to,
                    ),
                )
            ).scalar_one(),
        )
