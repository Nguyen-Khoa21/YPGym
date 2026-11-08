from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.models.attendance import AttendanceSession
from app.models.gym import GymLocation
from app.services.traffic_analytics_service import (
    calculate_traffic_summary,
    previous_completed_month,
    two_hour_window_label,
)


def test_previous_completed_month_uses_gym_timezone_and_handles_year_boundary():
    start, end = previous_completed_month(
        datetime(2026, 1, 15, 12, tzinfo=UTC),
        ZoneInfo("Asia/Ho_Chi_Minh"),
    )

    assert start.isoformat() == "2025-12-01T00:00:00+07:00"
    assert end.isoformat() == "2026-01-01T00:00:00+07:00"


def test_two_hour_labels_format_midnight_and_noon_naturally():
    assert two_hour_window_label(0) == "12:00 AM–2:00 AM"
    assert two_hour_window_label(10) == "10:00 AM–12:00 PM"
    assert two_hour_window_label(12) == "12:00 PM–2:00 PM"
    assert two_hour_window_label(22) == "10:00 PM–12:00 AM"


def test_traffic_summary_uses_session_overlap_and_caps_open_sessions():
    gym = GymLocation(
        id=uuid4(),
        name="Test Gym",
        slug="test-gym",
        district="Test District",
        address="Test District",
        timezone="UTC",
        capacity=10,
    )
    first_member = uuid4()
    sessions = [
        _session(first_member, datetime(2026, 10, 5, 14, tzinfo=UTC), datetime(2026, 10, 5, 16, tzinfo=UTC)),
        _session(uuid4(), datetime(2026, 10, 5, 15, tzinfo=UTC), datetime(2026, 10, 5, 17, tzinfo=UTC)),
        _session(uuid4(), datetime(2026, 9, 30, 23, 30, tzinfo=UTC), datetime(2026, 10, 1, 0, 30, tzinfo=UTC)),
        _session(uuid4(), datetime(2026, 10, 10, 10, tzinfo=UTC), None, status="active"),
    ]

    result = calculate_traffic_summary(
        gym=gym,
        sessions=sessions,
        generated_at=datetime(2026, 11, 8, 12, tzinfo=UTC),
        timeout_minutes=120,
    )

    assert result.data_sufficient
    assert result.period_start.isoformat() == "2026-10-01T00:00:00+00:00"
    assert result.period_end.isoformat() == "2026-11-01T00:00:00+00:00"
    assert result.sample_count == 31 * 24 * 4
    assert result.overlapping_sessions == 4
    assert result.visits == 3
    assert result.unique_members == 3
    assert result.busiest_window is not None
    assert result.busiest_window.label == "2:00 PM–4:00 PM"
    assert result.busiest_window.average_headcount > result.buckets[8].average_headcount
    assert result.quietest_window is not None
    assert result.quietest_window.label == "2:00 AM–4:00 AM"
    assert result.average_visit_minutes == 120
    assert len(result.buckets) == 12
    assert len(result.weekday_buckets) == 84


def test_traffic_summary_is_honest_when_data_is_insufficient():
    gym = GymLocation(
        id=uuid4(),
        name="Quiet Gym",
        slug="quiet-gym",
        district="Quiet District",
        address="Quiet District",
        timezone="UTC",
        capacity=100,
    )
    sessions = [
        _session(uuid4(), datetime(2026, 10, 5, 9, tzinfo=UTC), datetime(2026, 10, 5, 10, tzinfo=UTC)),
        _session(uuid4(), datetime(2026, 10, 6, 9, tzinfo=UTC), datetime(2026, 10, 6, 10, tzinfo=UTC)),
    ]

    result = calculate_traffic_summary(
        gym=gym,
        sessions=sessions,
        generated_at=datetime(2026, 11, 8, 12, tzinfo=UTC),
        timeout_minutes=180,
    )

    assert not result.data_sufficient
    assert result.insufficiency_reason == "Not enough attendance data yet"
    assert result.busiest_window is None
    assert result.quietest_window is None


def _session(user_id, checked_in_at, closed_at, *, status="checked_out"):
    return AttendanceSession(
        gym_id=uuid4(),
        user_id=user_id,
        checked_in_at=checked_in_at,
        closed_at=closed_at,
        status=status,
        source="iot_scanner",
    )
