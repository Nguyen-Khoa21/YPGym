from datetime import UTC, date, datetime
from decimal import Decimal
import pytest

from app.schemas.attendance_schema import CrowdednessResponse
from app.services.analytics_service import AnalyticsService


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.writes: list[tuple[str, int]] = []

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex: int) -> None:
        self.values[key] = value
        self.writes.append((key, ex))


class FakeAnalyticsRepository:
    async def membership_trends(self, **_: object):
        return [(date(2026, 9, 1), 1, 0, 0, 0, 0, 0, 0, 1)]

    async def class_popularity(self, **_: object):
        return [("Strength", 2, 8, 5, 20)]

    async def attendance_summary(self, **_: object):
        return (8, 5, Decimal("62.5"))

    async def revenue_summary(self, **_: object):
        return (2, Decimal("1500000.00"), Decimal("50000.00"))


class FakeAttendanceRepository:
    async def peak_hours(self, **_: object):
        return [(2, 18, 6)]


class FakeCrowdedness:
    async def get(self):
        return CrowdednessResponse(
            active_count=3,
            capacity=100,
            percentage=3,
            status="Low",
            calculated_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_manager_summary_uses_persisted_aggregates_and_bounded_cache() -> None:
    redis = FakeRedis()
    service = object.__new__(AnalyticsService)
    service.redis = redis
    service.analytics = FakeAnalyticsRepository()
    service.attendance = FakeAttendanceRepository()
    service.crowdedness = FakeCrowdedness()
    date_from = datetime(2026, 8, 15, tzinfo=UTC)
    date_to = datetime(2026, 9, 14, tzinfo=UTC)

    first = await service.summary(date_from=date_from, date_to=date_to)
    second = await service.summary(date_from=date_from, date_to=date_to)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert redis.writes[0][1] == 60
    assert first.class_popularity[0].utilization_percent == 40
    assert first.attendance.average_visit_minutes == 62.5
    assert first.revenue.gross_amount == Decimal("1500000.00")
    assert [point.period for point in first.membership_trends] == [date(2026, 8, 1), date(2026, 9, 1)]
