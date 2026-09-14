import json
from datetime import UTC, date, datetime

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.schemas.analytics_schema import (
    AnalyticsSummaryResponse,
    AttendanceAnalyticsSummary,
    ClassPopularityPoint,
    MembershipTrendPoint,
    RevenueAnalyticsSummary,
)
from app.services.attendance_service import CrowdednessService


class AnalyticsService:
    CACHE_TTL_SECONDS = 60
    CACHE_PREFIX = "ypgym:analytics:summary:"

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.redis = redis
        self.analytics = AnalyticsRepository(session)
        self.attendance = AttendanceRepository(session)
        self.crowdedness = CrowdednessService(session, redis)

    async def summary(self, *, date_from: datetime, date_to: datetime) -> AnalyticsSummaryResponse:
        date_from, date_to = date_from.astimezone(UTC), date_to.astimezone(UTC)
        cache_key = self._cache_key(date_from, date_to)
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                payload = AnalyticsSummaryResponse.model_validate_json(cached)
                return payload.model_copy(update={"cache_hit": True})
        except (RedisError, ValueError, json.JSONDecodeError):
            pass

        membership_rows, class_rows, attendance_row, revenue_row = await self._load_rows(date_from, date_to)
        peak_rows = await self.attendance.peak_hours(date_from=date_from, date_to=date_to)
        labels = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        busiest = max(peak_rows, key=lambda row: row[2]) if peak_rows else None
        attendance = AttendanceAnalyticsSummary(
            check_ins=int(attendance_row[0] or 0),
            unique_members=int(attendance_row[1] or 0),
            average_visit_minutes=round(float(attendance_row[2]), 1) if attendance_row[2] is not None else None,
            busiest_slot=f"{labels[busiest[0]]} {busiest[1]:02d}:00" if busiest else None,
            current_occupancy=await self.crowdedness.get(),
        )
        response = AnalyticsSummaryResponse(
            date_from=date_from,
            date_to=date_to,
            generated_at=datetime.now(UTC),
            cache_ttl_seconds=self.CACHE_TTL_SECONDS,
            membership_trends=self._membership_points(membership_rows, date_from, date_to),
            class_popularity=[
                ClassPopularityPoint(
                    class_type=str(row[0]),
                    class_count=int(row[1] or 0),
                    bookings=int(row[2] or 0),
                    unique_members=int(row[3] or 0),
                    capacity=int(row[4] or 0),
                    utilization_percent=round((int(row[2] or 0) / int(row[4])) * 100, 1) if row[4] else 0,
                )
                for row in class_rows
            ],
            attendance=attendance,
            revenue=RevenueAnalyticsSummary(
                successful_payments=int(revenue_row[0] or 0),
                gross_amount=revenue_row[1] or 0,
                discounts=revenue_row[2] or 0,
            ),
        )
        try:
            await self.redis.set(cache_key, response.model_dump_json(), ex=self.CACHE_TTL_SECONDS)
        except RedisError:
            pass
        return response

    async def _load_rows(self, date_from: datetime, date_to: datetime):
        return (
            await self.analytics.membership_trends(date_from=date_from, date_to=date_to),
            await self.analytics.class_popularity(date_from=date_from, date_to=date_to),
            await self.analytics.attendance_summary(date_from=date_from, date_to=date_to),
            await self.analytics.revenue_summary(date_from=date_from, date_to=date_to),
        )

    @classmethod
    def _cache_key(cls, date_from: datetime, date_to: datetime) -> str:
        return f"{cls.CACHE_PREFIX}{date_from.isoformat()}:{date_to.isoformat()}"

    @staticmethod
    def _membership_points(rows, date_from: datetime, date_to: datetime) -> list[MembershipTrendPoint]:
        by_period = {AnalyticsService._as_month(row[0]): row for row in rows}
        cursor = date(date_from.year, date_from.month, 1)
        last = date(date_to.year, date_to.month, 1)
        points: list[MembershipTrendPoint] = []
        while cursor <= last:
            row = by_period.get(cursor)
            points.append(
                MembershipTrendPoint(
                    period=cursor,
                    active=int(row[1] or 0) if row else 0,
                    expiring_soon=int(row[2] or 0) if row else 0,
                    frozen=int(row[3] or 0) if row else 0,
                    expired=int(row[4] or 0) if row else 0,
                    cancelled=int(row[5] or 0) if row else 0,
                    revoked=int(row[6] or 0) if row else 0,
                    pending_verification=int(row[7] or 0) if row else 0,
                    total=int(row[8] or 0) if row else 0,
                ),
            )
            cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
        return points

    @staticmethod
    def _as_month(value) -> date:
        if isinstance(value, datetime):
            return value.date().replace(day=1)
        return value.replace(day=1)
