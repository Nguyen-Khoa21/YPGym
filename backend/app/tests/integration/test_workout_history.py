from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.models.attendance import AttendanceEvent, AttendanceSession
from app.models.training import TrainingExercise, TrainingExerciseMuscle, WorkoutExercise, WorkoutSession, WorkoutSet

pytestmark = pytest.mark.asyncio


async def test_member_history_comparisons_and_weekly_map_share_snapshot_metric(client, storage, eligible_members):
    sessions, _ = storage
    users, headers = eligible_members
    timezone = ZoneInfo("Asia/Ho_Chi_Minh")

    async with sessions() as session:
        exercise = TrainingExercise(
            name="Original press",
            description="A stable illustrative pressing movement.",
            region="upper",
            usage_steps="Press with control through a comfortable range.",
            safety_note="Keep the movement controlled and stop if needed.",
        )
        session.add(exercise)
        await session.flush()
        session.add_all([
            TrainingExerciseMuscle(exercise_id=exercise.id, muscle="chest", role="primary"),
            TrainingExerciseMuscle(exercise_id=exercise.id, muscle="triceps", role="secondary"),
        ])

        async def add_day(member_index: int, day: date, sets: list[tuple[int, Decimal]], *, with_workout: bool = True) -> None:
            checked_in = datetime(day.year, day.month, day.day, 12, tzinfo=timezone).astimezone(UTC)
            attendance = AttendanceSession(user_id=users[member_index].id, checked_in_at=checked_in, status="checked_out", source="iot_scanner")
            session.add(attendance)
            await session.flush()
            session.add(AttendanceEvent(session_id=attendance.id, user_id=users[member_index].id, event_type="check_in", event_at=checked_in, source="iot_scanner"))
            if not with_workout:
                return
            workout = WorkoutSession(user_id=users[member_index].id, attendance_session_id=attendance.id, workout_date=day)
            session.add(workout)
            await session.flush()
            logged = WorkoutExercise(
                session_id=workout.id,
                exercise_id=exercise.id,
                idempotency_key=uuid4(),
                name_snapshot="Original press" if member_index == 0 else "Other member exercise",
                primary_muscles_snapshot=["chest"] if member_index == 0 else ["shoulders"],
                secondary_muscles_snapshot=["triceps"] if member_index == 0 else [],
                created_at=checked_in,
            )
            session.add(logged)
            await session.flush()
            session.add_all([
                WorkoutSet(workout_exercise_id=logged.id, set_order=index, reps=reps, weight=weight, unit="kg")
                for index, (reps, weight) in enumerate(sets, start=1)
            ])

        await add_day(0, date(2026, 12, 28), [(10, Decimal("0")), (8, Decimal("0"))])
        await add_day(0, date(2026, 12, 30), [], with_workout=False)
        await add_day(0, date(2027, 1, 3), [(12, Decimal("5")), (12, Decimal("5")), (10, Decimal("5"))])
        await add_day(1, date(2026, 12, 31), [(100, Decimal("100"))])
        exercise.name = "Renamed catalogue entry"
        await session.commit()

    history = await client.get(
        "/api/v1/training/workouts/history?date_from=2026-12-28&date_to=2027-01-03&page=1&page_size=2",
        headers=headers[0],
    )
    assert history.status_code == 200, history.text
    payload = history.json()
    assert payload["page"] == {"page": 1, "page_size": 2, "total": 3, "pages": 2}
    assert payload["metric"]["key"] == "weighted_set_exposure"
    assert payload["max_exposure_score"] == "4.5"
    assert [(item["workout_date"], item["attended"], item["has_workout"], item["intensity_level"]) for item in payload["items"]] == [
        ("2027-01-03", True, True, 4),
        ("2026-12-30", True, False, 0),
    ]

    page_two = (await client.get(
        "/api/v1/training/workouts/history?date_from=2026-12-28&date_to=2027-01-03&page=2&page_size=2",
        headers=headers[0],
    )).json()
    assert page_two["items"][0]["exposure_score"] == "3.0"
    assert page_two["items"][0]["set_count"] == 2
    assert page_two["items"][0]["intensity_level"] == 3

    detail = (await client.get("/api/v1/training/workouts/2027-01-03", headers=headers[0])).json()
    assert detail["session"]["exercises"][0]["name"] == "Original press"
    assert [(item["reps"], item["weight"]) for item in detail["session"]["exercises"][0]["sets"]] == [(12, "5.00"), (12, "5.00"), (10, "5.00")]
    attended_only = (await client.get("/api/v1/training/workouts/2026-12-30", headers=headers[0])).json()
    assert attended_only["attended"] is True and attended_only["session"] is None
    assert (await client.get("/api/v1/training/workouts/2026-12-29", headers=headers[0])).status_code == 404

    week = (await client.get("/api/v1/training/workouts/muscle-map?week_of=2027-01-01", headers=headers[0])).json()
    assert (week["week_start"], week["week_end"], week["total_exposure_score"]) == ("2026-12-28", "2027-01-03", "7.5")
    muscles = {item["muscle"]: item for item in week["muscles"]}
    assert muscles["chest"] == {"muscle": "chest", "exposure_score": "5.0", "intensity_level": 4}
    assert muscles["triceps"] == {"muscle": "triceps", "exposure_score": "2.5", "intensity_level": 2}
    assert muscles["shoulders"]["exposure_score"] == "0.0"
    assert len(week["days"]) == 7

    comparisons = (await client.get(f"/api/v1/training/exercises/{exercise.id}/history", headers=headers[0])).json()
    assert comparisons["page"]["total"] == 2
    assert comparisons["items"][0]["name"] == "Original press"
    assert comparisons["items"][0]["comparison_to_previous"] == {"sets": "more", "reps": "more", "external_load": "more"}
    assert comparisons["items"][1]["comparison_to_previous"] is None

    other_history = (await client.get(
        "/api/v1/training/workouts/history?date_from=2026-12-28&date_to=2027-01-03",
        headers=headers[1],
    )).json()
    assert [item["workout_date"] for item in other_history["items"]] == ["2026-12-31"]
    assert (await client.get(f"/api/v1/training/exercises/{exercise.id}/history", headers=headers[1])).json()["page"]["total"] == 1
    assert (await client.get("/api/v1/training/workouts/muscle-map?week_of=2027-01-01")).status_code == 401
    assert (await client.get("/api/v1/training/workouts/history?date_from=2027-01-03&date_to=2026-12-28", headers=headers[0])).status_code == 422


async def test_empty_week_has_zero_exposure_and_complete_days(client, eligible_members):
    _, headers = eligible_members
    response = await client.get("/api/v1/training/workouts/muscle-map?week_of=2026-01-01", headers=headers[2])
    assert response.status_code == 200
    payload = response.json()
    assert payload["week_start"] == "2025-12-29" and payload["week_end"] == "2026-01-04"
    assert payload["total_exposure_score"] == "0.0"
    assert len(payload["days"]) == 7 and all(item["intensity_level"] == 0 for item in payload["days"])
    assert len(payload["muscles"]) == 16 and all(item["intensity_level"] == 0 for item in payload["muscles"])
