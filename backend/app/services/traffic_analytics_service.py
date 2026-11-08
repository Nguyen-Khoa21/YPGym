import json
from datetime import UTC, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models.attendance import AttendanceSession
from app.models.gym import GymLocation
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.gym_repository import GymRepository
from app.schemas.analytics_schema import (
    TrafficMethodology,
    TrafficSummaryResponse,
    TrafficWindowPoint,
    WeekdayTrafficWindow,
)
from app.services.configuration_service import ConfigurationService


SAMPLE_INTERVAL_MINUTES = 15
BUCKET_HOURS = 2
MINIMUM_SESSIONS = 3
DEMO_SOURCES = {"development_seed", "release_demo", "multigym_demo"}
WEEKDAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def previous_completed_month(now: datetime, timezone: ZoneInfo) -> tuple[datetime, datetime]:
    local_now = now.astimezone(timezone)
    current_month = local_now.date().replace(day=1)
    previous_month_end = current_month - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)
    return (
        datetime.combine(previous_month_start, time.min, timezone),
        datetime.combine(current_month, time.min, timezone),
    )


def two_hour_window_label(start_hour: int) -> str:
    return f"{_hour_label(start_hour)}–{_hour_label(start_hour + BUCKET_HOURS)}"


def calculate_traffic_summary(
    *,
    gym: GymLocation,
    sessions: list[AttendanceSession],
    generated_at: datetime,
    timeout_minutes: int,
) -> TrafficSummaryResponse:
    timezone = ZoneInfo(gym.timezone)
    period_start, period_end = previous_completed_month(generated_at, timezone)
    period_start_utc = period_start.astimezone(UTC)
    period_end_utc = period_end.astimezone(UTC)
    timeout = timedelta(minutes=timeout_minutes)
    intervals: list[tuple[AttendanceSession, datetime, datetime]] = []
    for attendance_session in sessions:
        checked_in_at = _as_utc(attendance_session.checked_in_at)
        raw_end = (
            _as_utc(attendance_session.closed_at)
            if attendance_session.closed_at
            else checked_in_at + timeout
        )
        interval_start = max(checked_in_at, period_start_utc)
        interval_end = min(raw_end, period_end_utc)
        if interval_end > interval_start:
            intervals.append((attendance_session, interval_start, interval_end))

    bucket_totals = {hour: [0, 0] for hour in range(0, 24, BUCKET_HOURS)}
    weekday_totals = {
        (weekday, hour): [0, 0]
        for weekday in range(7)
        for hour in range(0, 24, BUCKET_HOURS)
    }
    sample_at = period_start_utc
    sample_step = timedelta(minutes=SAMPLE_INTERVAL_MINUTES)
    interval_starts = sorted(starts_at for _, starts_at, _ in intervals)
    interval_ends = sorted(ends_at for _, _, ends_at in intervals)
    started = 0
    ended = 0
    total_headcount = 0
    sample_count = 0
    while sample_at < period_end_utc:
        while started < len(interval_starts) and interval_starts[started] <= sample_at:
            started += 1
        while ended < len(interval_ends) and interval_ends[ended] <= sample_at:
            ended += 1
        headcount = started - ended
        local_sample = sample_at.astimezone(timezone)
        bucket_hour = (local_sample.hour // BUCKET_HOURS) * BUCKET_HOURS
        bucket_totals[bucket_hour][0] += headcount
        bucket_totals[bucket_hour][1] += 1
        weekday_totals[(local_sample.weekday(), bucket_hour)][0] += headcount
        weekday_totals[(local_sample.weekday(), bucket_hour)][1] += 1
        total_headcount += headcount
        sample_count += 1
        sample_at += sample_step

    buckets = [
        _window_point(hour, *bucket_totals[hour], capacity=gym.capacity)
        for hour in range(0, 24, BUCKET_HOURS)
    ]
    weekday_buckets = [
        WeekdayTrafficWindow(
            weekday=weekday,
            weekday_label=WEEKDAY_LABELS[weekday],
            **_window_point(hour, *weekday_totals[(weekday, hour)], capacity=gym.capacity).model_dump(),
        )
        for weekday in range(7)
        for hour in range(0, 24, BUCKET_HOURS)
    ]
    visits = [
        (attendance_session, starts_at, ends_at)
        for attendance_session, starts_at, ends_at in intervals
        if period_start_utc <= _as_utc(attendance_session.checked_in_at) < period_end_utc
    ]
    average_visit_minutes = (
        round(
            sum((ends_at - max(_as_utc(item.checked_in_at), period_start_utc)).total_seconds() for item, _, ends_at in visits)
            / len(visits)
            / 60,
            1,
        )
        if visits
        else None
    )
    data_sufficient = len(intervals) >= MINIMUM_SESSIONS
    average_headcount = round(total_headcount / sample_count, 2) if sample_count else 0.0
    return TrafficSummaryResponse(
        gym_id=gym.id,
        gym_name=gym.name,
        gym_slug=gym.slug,
        district=gym.district,
        capacity=gym.capacity,
        timezone=gym.timezone,
        period_start=period_start,
        period_end=period_end,
        generated_at=generated_at,
        data_sufficient=data_sufficient,
        insufficiency_reason=None if data_sufficient else "Not enough attendance data yet",
        contains_demo_data=any(item.source in DEMO_SOURCES for item, _, _ in intervals),
        overlapping_sessions=len(intervals),
        visits=len(visits),
        unique_members=len({item.user_id for item, _, _ in visits}),
        average_visit_minutes=average_visit_minutes,
        sample_count=sample_count,
        average_headcount=average_headcount,
        average_capacity_percentage=round((average_headcount / gym.capacity) * 100, 1),
        busiest_window=(
            max(buckets, key=lambda item: (item.average_headcount, -item.start_hour))
            if data_sufficient
            else None
        ),
        quietest_window=(
            min(buckets, key=lambda item: (item.average_headcount, item.start_hour))
            if data_sufficient
            else None
        ),
        buckets=buckets,
        weekday_buckets=weekday_buckets,
        methodology=TrafficMethodology(
            minimum_sessions=MINIMUM_SESSIONS,
            session_end_rule=(
                "Closed sessions use their recorded close time; open sessions are capped at the configured "
                f"{timeout_minutes}-minute attendance timeout. The reporting period end is exclusive."
            ),
        ),
    )


class TrafficAnalyticsService:
    CACHE_PREFIX = "ypgym:analytics:traffic-summary:"
    CACHE_TTL_SECONDS = 300

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.redis = redis
        self.analytics = AnalyticsRepository(session)
        self.gyms = GymRepository(session)
        self.configuration = ConfigurationService(session, redis)

    async def get(
        self,
        *,
        gym_id: UUID,
        now: datetime | None = None,
        force_recompute: bool = False,
    ) -> TrafficSummaryResponse:
        gym = await self.gyms.get_location(gym_id, active_only=True)
        if not gym:
            raise ResourceNotFoundError("The gym location could not be found.")
        generated_at = now or datetime.now(UTC)
        period_start, period_end = previous_completed_month(generated_at, ZoneInfo(gym.timezone))
        cache_key = f"{self.CACHE_PREFIX}{gym.id}:{period_start.date().isoformat()}"
        if not force_recompute:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    return TrafficSummaryResponse.model_validate_json(cached).model_copy(
                        update={"cache_hit": True},
                    )
            except (RedisError, ValueError, json.JSONDecodeError):
                pass
        sessions = await self.analytics.attendance_sessions_overlapping(
            gym_id=gym.id,
            period_start=period_start.astimezone(UTC),
            period_end=period_end.astimezone(UTC),
        )
        response = calculate_traffic_summary(
            gym=gym,
            sessions=sessions,
            generated_at=generated_at,
            timeout_minutes=await self.configuration.get_int("attendance_timeout_minutes"),
        )
        try:
            await self.redis.set(cache_key, response.model_dump_json(), ex=self.CACHE_TTL_SECONDS)
        except RedisError:
            pass
        return response


def _window_point(start_hour: int, total: int, samples: int, *, capacity: int) -> TrafficWindowPoint:
    average_headcount = round(total / samples, 2) if samples else 0.0
    return TrafficWindowPoint(
        start_hour=start_hour,
        end_hour=start_hour + BUCKET_HOURS,
        label=two_hour_window_label(start_hour),
        average_headcount=average_headcount,
        average_capacity_percentage=round((average_headcount / capacity) * 100, 1),
        sample_count=samples,
    )


def _hour_label(hour: int) -> str:
    normalized = hour % 24
    suffix = "AM" if normalized < 12 else "PM"
    value = normalized % 12 or 12
    return f"{value}:00 {suffix}"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
