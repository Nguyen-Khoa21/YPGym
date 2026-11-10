from types import SimpleNamespace
from uuid import uuid4

from app.schemas.analytics_schema import TrafficWindowPoint
from app.services.onboarding_service import pick_quiet_window, profile_status


def bucket(start: int, headcount: float) -> TrafficWindowPoint:
    return TrafficWindowPoint(
        start_hour=start,
        end_hour=start + 2,
        label=f"{start}",
        average_headcount=headcount,
        average_capacity_percentage=headcount,
        sample_count=10,
    )


def profile(**values):
    base = dict(
        is_new_to_gym=None,
        prefers_uncrowded_hours=None,
        closer_gym_id=None,
        main_goal=None,
        training_window=None,
        days_per_week=None,
        interested_in_classes=None,
        interested_in_personal_trainer=None,
        dismissed_at=None,
    )
    base.update(values)
    return SimpleNamespace(**base)


def test_status_matrix():
    assert profile_status(None) == "not_started"
    assert profile_status(profile()) == "not_started"
    assert profile_status(profile(dismissed_at="x")) == "skipped"
    assert profile_status(profile(is_new_to_gym=True)) == "partial"
    assert profile_status(profile(is_new_to_gym=False, prefers_uncrowded_hours=False, closer_gym_id=uuid4())) == "complete"
    # Q1 to Q3 are required: extras alone never make a profile complete.
    assert profile_status(profile(main_goal="stamina", interested_in_classes=True)) == "partial"


def test_quiet_window_is_quietest_overall_without_a_training_window():
    buckets = [bucket(6, 20), bucket(10, 4), bucket(18, 30)]
    assert pick_quiet_window(buckets, None).start_hour == 10


def test_quiet_window_stays_inside_the_training_window():
    buckets = [bucket(6, 20), bucket(10, 4), bucket(18, 30), bucket(20, 12)]
    assert pick_quiet_window(buckets, "evening").start_hour == 18
    assert pick_quiet_window(buckets, "night").start_hour == 20
    assert pick_quiet_window(buckets, "early_morning").start_hour == 6


def test_quiet_window_ties_pick_the_earlier_window():
    assert pick_quiet_window([bucket(14, 5), bucket(10, 5)], None).start_hour == 10


def test_quiet_window_absent_when_nothing_overlaps():
    assert pick_quiet_window([bucket(10, 4)], "night") is None
