import json
from datetime import UTC, date, datetime, time, timedelta
from hmac import compare_digest
from math import ceil
from uuid import UUID, uuid4

from jose import ExpiredSignatureError, JWTError, jwt
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, DependencyUnavailableError, ResourceNotFoundError
from app.core.rate_limit import rate_limits
from app.models.attendance import AttendanceEvent, AttendanceSession, IoTDevice
from app.models.user import User
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.operations_repository import AuditRepository
from app.schemas.attendance_schema import (
    AttendanceEventItem,
    AttendancePage,
    AttendanceSessionItem,
    CrowdednessResponse,
    PeakHourCell,
    PeakHoursResponse,
    QrTokenResponse,
    ScannerResponse,
)
from app.schemas.operations_schema import PageInfo
from app.services.configuration_service import ConfigurationService
from app.services.lifecycle_service import MembershipLifecycleService
from app.utils.security import hash_token


def crowdedness_status(percentage: float) -> str:
    if percentage <= 30:
        return "Low"
    if percentage <= 60:
        return "Moderate"
    if percentage <= 85:
        return "Busy"
    return "Very Crowded"


class CrowdednessService:
    CACHE_KEY = "ypgym:attendance:occupancy"

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.attendance = AttendanceRepository(session)
        self.configuration = ConfigurationService(session, redis)

    async def get(self, *, force_reconcile: bool = False) -> CrowdednessResponse:
        if not force_reconcile:
            try:
                cached = await self.redis.get(self.CACHE_KEY)
                if cached:
                    parsed = json.loads(cached)
                    return CrowdednessResponse.model_validate(parsed)
            except (RedisError, json.JSONDecodeError, ValueError):
                pass
        active_count = await self.attendance.active_count()
        capacity = await self.configuration.get_int("gym_capacity")
        percentage = round((active_count / capacity) * 100, 1) if capacity > 0 else 0.0
        response = CrowdednessResponse(
            active_count=active_count,
            capacity=capacity,
            percentage=percentage,
            status=crowdedness_status(percentage),
            calculated_at=datetime.now(UTC),
        )
        try:
            await self.redis.set(self.CACHE_KEY, response.model_dump_json(), ex=30)
        except RedisError:
            pass
        return response


class QrTokenService:
    ACTIVE_PREFIX = "ypgym:attendance:qr:active:"
    JTI_PREFIX = "ypgym:attendance:qr:jti:"

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.configuration = ConfigurationService(session, redis)
        self.lifecycle = MembershipLifecycleService(session)
        self.settings = get_settings()

    async def generate(self, user: User) -> QrTokenResponse:
        membership = await self.lifecycle.require_eligible_membership(user)
        ttl = await self.configuration.get_int("qr_token_ttl_seconds")
        issued_at = datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=ttl)
        jti = uuid4().hex
        payload = {
            "sub": str(user.id),
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": jti,
            "type": "attendance_qr",
        }
        token = jwt.encode(payload, self.settings.JWT_SECRET_KEY, algorithm=self.settings.JWT_ALGORITHM)
        active_key = f"{self.ACTIVE_PREFIX}{user.id}"
        try:
            previous_jti = await self.redis.get(active_key)
            pipe = self.redis.pipeline(transaction=True)
            if previous_jti:
                pipe.delete(f"{self.JTI_PREFIX}{previous_jti}")
            pipe.set(active_key, jti, ex=ttl)
            pipe.set(f"{self.JTI_PREFIX}{jti}", str(user.id), ex=ttl)
            await pipe.execute()
        except RedisError as exc:
            raise DependencyUnavailableError(
                "QR_STATE_UNAVAILABLE",
                "A rotating QR token cannot be issued while token state is unavailable.",
            ) from exc
        await self.session.commit()
        return QrTokenResponse(
            token=token,
            issued_at=issued_at,
            expires_at=expires_at,
            ttl_seconds=ttl,
            membership_status=membership.status,
        )

    async def validate(self, token: str) -> tuple[UUID, str]:
        try:
            payload = jwt.decode(
                token,
                self.settings.JWT_SECRET_KEY,
                algorithms=[self.settings.JWT_ALGORITHM],
            )
        except ExpiredSignatureError as exc:
            raise AppError("EXPIRED_TOKEN", "The QR token has expired.", 400) from exc
        except JWTError as exc:
            raise AppError("INVALID_TOKEN", "The QR token is invalid.", 400) from exc
        if payload.get("type") != "attendance_qr" or not payload.get("sub") or not payload.get("jti"):
            raise AppError("INVALID_TOKEN", "The QR token payload is invalid.", 400)
        try:
            user_id = UUID(str(payload["sub"]))
        except ValueError as exc:
            raise AppError("INVALID_TOKEN", "The QR token member identifier is invalid.", 400) from exc
        jti = str(payload["jti"])
        try:
            tracked_user, active_jti = await self.redis.mget(
                f"{self.JTI_PREFIX}{jti}",
                f"{self.ACTIVE_PREFIX}{user_id}",
            )
        except RedisError as exc:
            raise DependencyUnavailableError(
                "QR_STATE_UNAVAILABLE",
                "QR token state cannot be verified right now.",
            ) from exc
        if active_jti and active_jti != jti:
            raise AppError("SUPERSEDED_TOKEN", "A newer QR token has replaced this one.", 409)
        if tracked_user != str(user_id) or active_jti != jti:
            raise AppError("INVALID_TOKEN", "The QR token is no longer active.", 400)
        return user_id, jti


class AttendanceService:
    DUPLICATE_PREFIX = "ypgym:attendance:scan:"

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.attendance = AttendanceRepository(session)
        self.audit = AuditRepository(session)
        self.configuration = ConfigurationService(session, redis)
        self.qr = QrTokenService(session, redis)
        self.crowdedness = CrowdednessService(session, redis)
        self.settings = get_settings()

    async def check_in(self, *, device_id: str, api_key: str, qr_token: str) -> ScannerResponse:
        device = await self._authenticate_device(device_id, api_key)
        user_id, jti = await self.qr.validate(qr_token)
        user = await self.session.get(User, user_id)
        if not user:
            raise AppError("INVALID_TOKEN", "The QR token member no longer exists.", 400)
        try:
            await MembershipLifecycleService(self.session).require_eligible_membership(user)
        except AppError as exc:
            if exc.code in {"MEMBERSHIP_INELIGIBLE", "MEMBERSHIP_REQUIRED"}:
                raise AppError("INACTIVE_MEMBERSHIP", exc.message, 403, exc.details) from exc
            raise
        duplicate_window = await self.configuration.get_int("duplicate_scan_window_seconds")
        duplicate_key = f"{self.DUPLICATE_PREFIX}{jti}"
        try:
            accepted = await self.redis.set(duplicate_key, "1", ex=duplicate_window, nx=True)
        except RedisError as exc:
            raise DependencyUnavailableError(
                "SCAN_STATE_UNAVAILABLE",
                "Duplicate scan protection is unavailable.",
            ) from exc
        if not accepted:
            raise AppError("DUPLICATE_SCAN", "This QR token was scanned too recently.", 409)
        if await self.attendance.get_active_session(user_id, for_update=True):
            raise AppError("ACTIVE_SESSION_EXISTS", "This member already has an active attendance session.", 409)
        now = datetime.now(UTC)
        try:
            attendance_session = await self.attendance.create_session(
                user_id=user_id,
                checked_in_at=now,
                source="iot_scanner",
                device_id=device.device_id,
            )
            await self.attendance.create_event(
                attendance_session=attendance_session,
                event_type="check_in",
                event_at=now,
                source="iot_scanner",
                device_id=device.device_id,
                metadata={"qr_jti_hash": hash_token(jti)},
            )
            device.last_seen_at = now
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError("ACTIVE_SESSION_EXISTS", "This member already has an active attendance session.", 409) from exc
        except SQLAlchemyError as exc:
            await self.session.rollback()
            try:
                await self.redis.delete(duplicate_key)
            except RedisError:
                pass
            raise AppError("INTERNAL_FAILURE", "The attendance session could not be created.", 500) from exc
        occupancy = await self.crowdedness.get(force_reconcile=True)
        return ScannerResponse(
            code="CHECK_IN_SUCCESS",
            message="Check-in recorded.",
            session_id=attendance_session.id,
            member_id=user_id,
            occurred_at=now,
            occupancy=occupancy,
        )

    async def check_out(self, *, device_id: str, api_key: str, qr_token: str) -> ScannerResponse:
        device = await self._authenticate_device(device_id, api_key)
        user_id, _ = await self.qr.validate(qr_token)
        attendance_session = await self.attendance.get_active_session(user_id, for_update=True)
        if not attendance_session:
            raise AppError("NO_ACTIVE_SESSION", "This member has no active attendance session.", 409)
        now = datetime.now(UTC)
        attendance_session.status = "checked_out"
        attendance_session.closed_at = now
        await self.attendance.create_event(
            attendance_session=attendance_session,
            event_type="check_out",
            event_at=now,
            source="iot_scanner",
            device_id=device.device_id,
        )
        device.last_seen_at = now
        await self.session.commit()
        occupancy = await self.crowdedness.get(force_reconcile=True)
        return ScannerResponse(
            code="CHECK_OUT_SUCCESS",
            message="Check-out recorded.",
            session_id=attendance_session.id,
            member_id=user_id,
            occurred_at=now,
            occupancy=occupancy,
        )

    async def manual_close(self, *, session_id: UUID, actor: User, reason: str) -> AttendanceSessionItem:
        attendance_session = await self.attendance.get_session(session_id, for_update=True)
        if not attendance_session:
            raise ResourceNotFoundError("Attendance session was not found.")
        events = await self.attendance.events_for_sessions([attendance_session.id])
        if attendance_session.status != "active":
            return self._session_item(attendance_session, events.get(attendance_session.id, []))
        now = datetime.now(UTC)
        attendance_session.status = "manual_closed"
        attendance_session.closed_at = now
        attendance_session.closed_by_id = actor.id
        attendance_session.manual_close_reason = reason.strip()
        event = await self.attendance.create_event(
            attendance_session=attendance_session,
            event_type="manual_close",
            event_at=now,
            source="staff_console",
            device_id=attendance_session.device_id,
            metadata={"reason": reason.strip()},
        )
        await self.audit.create(
            actor_user_id=actor.id,
            target_user_id=attendance_session.user_id,
            action="attendance.manual_closed",
            entity_type="attendance_session",
            entity_id=str(attendance_session.id),
            reason=reason.strip(),
            outcome="manual_closed",
            summary="An active attendance session was manually closed.",
        )
        await self.session.commit()
        await self.crowdedness.get(force_reconcile=True)
        return self._session_item(attendance_session, [*events.get(attendance_session.id, []), event])

    async def close_timed_out_sessions(self) -> int:
        timeout_minutes = await self.configuration.get_int("attendance_timeout_minutes")
        now = datetime.now(UTC)
        candidates = await self.attendance.timeout_candidates(now - timedelta(minutes=timeout_minutes))
        for attendance_session in candidates:
            if attendance_session.status != "active":
                continue
            attendance_session.status = "timed_out"
            attendance_session.closed_at = now
            await self.attendance.create_event(
                attendance_session=attendance_session,
                event_type="timeout",
                event_at=now,
                source="timeout_worker",
                device_id=attendance_session.device_id,
                metadata={"timeout_minutes": timeout_minutes},
            )
        await self.session.commit()
        if candidates:
            await self.crowdedness.get(force_reconcile=True)
        return len(candidates)

    async def member_history(self, *, user: User, page: int, page_size: int) -> AttendancePage:
        sessions, total, events = await self.attendance.list_member_sessions(
            user_id=user.id,
            page=page,
            page_size=page_size,
        )
        return AttendancePage(
            items=[self._session_item(item, events.get(item.id, [])) for item in sessions],
            page=PageInfo(page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0),
            distinct_visit_days=await self.attendance.distinct_member_visit_days(
                user_id=user.id,
                gym_timezone=self.settings.GYM_TIMEZONE,
            ),
            gym_timezone=self.settings.GYM_TIMEZONE,
        )

    async def admin_history(self, **filters) -> AttendancePage:
        rows, total, events = await self.attendance.list_admin_sessions(**filters)
        return AttendancePage(
            items=[
                self._session_item(item, events.get(item.id, []), member_name=user.name, member_email=user.email)
                for item, user in rows
            ],
            page=PageInfo(
                page=filters["page"],
                page_size=filters["page_size"],
                total=total,
                pages=ceil(total / filters["page_size"]) if total else 0,
            ),
        )

    async def peak_hours(self, *, date_from: datetime, date_to: datetime) -> PeakHoursResponse:
        raw = await self.attendance.peak_hours(date_from=date_from, date_to=date_to)
        counts = {(weekday, hour): visits for weekday, hour, visits in raw}
        labels = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        cells = [
            PeakHourCell(weekday=weekday, weekday_label=labels[weekday], hour=hour, visits=counts.get((weekday, hour), 0))
            for weekday in range(7)
            for hour in range(24)
        ]
        busiest = max(raw, key=lambda row: row[2]) if raw else None
        today_start = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
        visits_today = await self.attendance.visits_between(
            date_from=today_start,
            date_to=today_start + timedelta(days=1),
        )
        return PeakHoursResponse(
            cells=cells,
            occupancy=await self.crowdedness.get(),
            visits_today=visits_today,
            busiest_hour=f"{labels[busiest[0]]} {busiest[1]:02d}:00" if busiest else None,
            date_from=date_from,
            date_to=date_to,
        )

    async def _authenticate_device(self, device_id: str, api_key: str) -> IoTDevice:
        if not api_key:
            raise AppError("INVALID_DEVICE", "Device credentials are required.", 401)
        device = await self.attendance.get_device_for_update(device_id)
        if not device or not device.is_active or not compare_digest(device.api_key_hash, hash_token(api_key)):
            raise AppError("INVALID_DEVICE", "Device credentials are invalid.", 401)
        await rate_limits.enforce(
            self.redis, key=f"ypgym:rate:scanner:{hash_token(device.device_id)}", limit=60, window_seconds=60,
        )
        return device

    @staticmethod
    def _session_item(
        attendance_session: AttendanceSession,
        events: list[AttendanceEvent],
        *,
        member_name: str | None = None,
        member_email: str | None = None,
    ) -> AttendanceSessionItem:
        return AttendanceSessionItem(
            id=attendance_session.id,
            user_id=attendance_session.user_id,
            member_name=member_name,
            member_email=member_email,
            checked_in_at=attendance_session.checked_in_at,
            closed_at=attendance_session.closed_at,
            status=attendance_session.status,
            source=attendance_session.source,
            device_id=attendance_session.device_id,
            manual_close_reason=attendance_session.manual_close_reason,
            events=[
                AttendanceEventItem(
                    id=event.id,
                    event_type=event.event_type,
                    event_at=event.event_at,
                    source=event.source,
                    device_id=event.device_id,
                )
                for event in events
            ],
        )
