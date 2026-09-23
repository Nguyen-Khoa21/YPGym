import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.attendance import IoTDevice
from app.models.membership import UserMembership
from app.models.training import TrainingExercise, TrainingExerciseMuscle, WorkoutExercise, WorkoutSession, WorkoutSet
from app.services.workout_service import WorkoutService
from app.utils.security import hash_token

pytestmark = pytest.mark.asyncio


async def test_workout_requires_real_check_in_and_preserves_shared_history(client, storage, eligible_members):
    sessions, _ = storage
    users, headers = eligible_members
    async with sessions() as session:
        exercise = TrainingExercise(name="Bodyweight row", description="Illustrative pulling exercise.", region="upper", usage_steps="Pull with control while keeping the body aligned.", safety_note="Use a stable bar and controlled range.")
        session.add_all([exercise, IoTDevice(device_id="training-door", display_name="Training door", api_key_hash=hash_token("training-key"))])
        await session.flush()
        session.add(TrainingExerciseMuscle(exercise_id=exercise.id, muscle="back", role="primary"))
        await session.commit()
    url = "/api/v1/training/workouts/today"
    payload = {"exercise_id": str(exercise.id), "idempotency_key": str(uuid4()), "sets": [{"reps": 12, "weight": "0", "unit": "kg"}, {"reps": 10, "weight": "15.5", "unit": "lb"}]}
    assert (await client.get(url, headers=headers[0])).json()["eligible"] is False
    denied = await client.post(f"{url}/exercises", headers=headers[0], json=payload)
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "WORKOUT_CHECK_IN_REQUIRED"
    assert (await client.post(f"{url}/exercises", headers=headers[1], json=payload)).status_code == 403
    assert (await client.get(url)).status_code == 401
    qr = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).json()["token"]
    scanner = {"X-Device-Api-Key": "training-key"}
    scan = await client.post("/api/v1/attendance/check-in", headers=scanner, json={"device_id": "training-door", "qr_token": qr})
    assert scan.status_code == 200, scan.text
    bad = await client.post(f"{url}/exercises", headers=headers[0], json={**payload, "sets": [{"reps": 0, "weight": "0", "unit": "kg"}]})
    assert bad.status_code == 422
    for weight in ["-1", "1.234", "10000"]:
        assert (await client.post(f"{url}/exercises", headers=headers[0], json={**payload, "sets": [{"reps": 10, "weight": weight, "unit": "kg"}]})).status_code == 422
    assert (await client.post(f"{url}/exercises", headers=headers[0], json={**payload, "sets": []})).status_code == 422
    saved = await client.post(f"{url}/exercises", headers=headers[0], json=payload)
    assert saved.status_code == 200, saved.text
    workout = saved.json()["session"]
    assert saved.json()["eligible"] is True and workout["attendance_session_id"] == scan.json()["session_id"]
    assert workout["exercises"][0]["name"] == "Bodyweight row"
    assert [(row["reps"], row["weight"], row["unit"]) for row in workout["exercises"][0]["sets"]] == [(12, "0.00", "kg"), (10, "15.50", "lb")]
    assert (await client.post(f"{url}/exercises", headers=headers[0], json=payload)).json()["session"]["exercises"][0]["id"] == workout["exercises"][0]["id"]
    assert (await client.post(f"{url}/exercises", headers=headers[0], json={**payload, "sets": [{"reps": 5, "weight": "0", "unit": "kg"}]})).status_code == 409
    assert (await client.get(url, headers=headers[1])).json()["session"] is None
    assert (await client.post("/api/v1/attendance/check-out", headers=scanner, json={"device_id": "training-door", "qr_token": qr})).status_code == 200
    assert (await client.get(url, headers=headers[0])).json()["session"]["id"] == workout["id"]
    async with sessions() as session:
        row = await session.get(TrainingExercise, exercise.id)
        row.name = "Renamed later"
        row.is_active = False
        await session.commit()
    assert (await client.get(url, headers=headers[0])).json()["session"]["exercises"][0]["name"] == "Bodyweight row"
    assert (await client.post(f"{url}/exercises", headers=headers[0], json={**payload, "idempotency_key": str(uuid4())})).status_code == 404
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == users[0].id))).scalar_one()
        membership.status = "revoked"
        await session.commit()
    assert (await client.get(url, headers=headers[0])).json()["session"]["id"] == workout["id"]
    assert (await client.get(url, headers=headers[0])).json()["eligible"] is False
    assert (await client.post(f"{url}/exercises", headers=headers[0], json={**payload, "idempotency_key": str(uuid4())})).status_code == 403
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(WorkoutSession)) == 1
        assert await session.scalar(select(func.count()).select_from(WorkoutExercise)) == 1
        assert await session.scalar(select(func.count()).select_from(WorkoutSet)) == 2


async def test_concurrent_workout_writes_share_one_day(client, storage, eligible_members):
    sessions, _ = storage
    users, headers = eligible_members
    async with sessions() as session:
        exercise = TrainingExercise(name="Squat", description="Illustrative lower body movement.", region="lower", usage_steps="Stand tall and bend with control.", safety_note="Keep a stable stance and controlled range.")
        session.add_all([exercise, IoTDevice(device_id="workout-door", display_name="Workout door", api_key_hash=hash_token("workout-key"))])
        await session.flush()
        session.add(TrainingExerciseMuscle(exercise_id=exercise.id, muscle="quadriceps", role="primary"))
        await session.commit()
    qr = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).json()["token"]
    assert (await client.post("/api/v1/attendance/check-in", headers={"X-Device-Api-Key": "workout-key"}, json={"device_id": "workout-door", "qr_token": qr})).status_code == 200
    url = "/api/v1/training/workouts/today/exercises"
    payload = {"exercise_id": str(exercise.id), "idempotency_key": str(uuid4()), "sets": [{"reps": 10, "weight": "0", "unit": "kg"}]}
    results = await asyncio.gather(client.post(url, headers=headers[0], json=payload), client.post(url, headers=headers[0], json=payload))
    assert [result.status_code for result in results] == [200, 200], [result.text for result in results]
    assert results[0].json()["session"]["id"] == results[1].json()["session"]["id"]
    second = await asyncio.gather(client.post(url, headers=headers[0], json={**payload, "idempotency_key": str(uuid4())}), client.post(url, headers=headers[0], json={**payload, "idempotency_key": str(uuid4())}))
    assert [result.status_code for result in second] == [200, 200]
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(WorkoutSession)) == 1
        assert await session.scalar(select(func.count()).select_from(WorkoutExercise)) == 3


async def test_gym_local_day_boundary(storage):
    sessions, _ = storage
    async with sessions() as session:
        service = WorkoutService(session)
        before = service._today_window(datetime(2026, 9, 21, 16, 59, tzinfo=UTC))
        after = service._today_window(datetime(2026, 9, 21, 17, 0, tzinfo=UTC))
        assert str(before[0]) == "2026-09-21"
        assert str(after[0]) == "2026-09-22"
        assert before[2] == after[1]
