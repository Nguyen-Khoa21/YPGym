import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.attendance import AttendanceEvent, AttendanceSession, IoTDevice
from app.models.gym import (
    DISTRICT_1_GYM_ID,
    DISTRICT_11_GYM_ID,
    GymLocation,
    WorkforceGymAssignment,
)
from app.models.membership import UserMembership
from app.models.user import User
from app.services.attendance_service import CrowdednessService
from app.services.attendance_realtime_service import AttendanceRealtimePublisher
from app.utils.security import create_access_token, hash_token
from app.workers.celery_app import close_timed_out_attendance


pytestmark = pytest.mark.asyncio


async def test_scanners_memberships_occupancy_and_cache_are_isolated_by_gym(
    client,
    storage,
    eligible_members,
):
    sessions, redis = storage
    users, headers = eligible_members
    async with sessions() as session:
        district_11_membership = (
            await session.execute(
                select(UserMembership).where(UserMembership.user_id == users[1].id),
            )
        ).scalar_one()
        district_11_membership.home_gym_id = DISTRICT_11_GYM_ID
        district_11_gym = await session.get(GymLocation, DISTRICT_11_GYM_ID)
        assert district_11_gym is not None
        district_11_gym.capacity = 75
        session.add_all(
            [
                IoTDevice(
                    gym_id=DISTRICT_1_GYM_ID,
                    device_id="isolation-door-1",
                    display_name="District 1 door",
                    api_key_hash=hash_token("isolation-key"),
                ),
                IoTDevice(
                    gym_id=DISTRICT_11_GYM_ID,
                    device_id="isolation-door-11",
                    display_name="District 11 door",
                    api_key_hash=hash_token("isolation-key"),
                ),
            ],
        )
        await session.commit()

    district_1_token = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).json()["token"]
    district_11_token = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[1])).json()["token"]
    scanner_headers = {"X-Device-Api-Key": "isolation-key"}

    wrong_gym = await client.post(
        "/api/v1/attendance/check-in",
        headers=scanner_headers,
        json={"device_id": "isolation-door-11", "qr_token": district_1_token},
    )
    assert wrong_gym.status_code == 403
    assert wrong_gym.json()["error"]["code"] == "MEMBERSHIP_GYM_MISMATCH"

    district_1 = await client.post(
        "/api/v1/attendance/check-in",
        headers=scanner_headers,
        json={
            "device_id": "isolation-door-1",
            "qr_token": district_1_token,
            "gym_id": str(DISTRICT_11_GYM_ID),
        },
    )
    district_11 = await client.post(
        "/api/v1/attendance/check-in",
        headers=scanner_headers,
        json={"device_id": "isolation-door-11", "qr_token": district_11_token},
    )
    assert district_1.status_code == district_11.status_code == 200
    assert district_1.json()["gym_id"] == str(DISTRICT_1_GYM_ID)
    assert district_11.json()["gym_id"] == str(DISTRICT_11_GYM_ID)
    assert district_1.json()["occupancy"]["active_count"] == 1
    assert district_11.json()["occupancy"]["active_count"] == 1
    assert district_1.json()["occupancy"]["capacity"] == 150
    assert district_11.json()["occupancy"]["capacity"] == 75

    crowdedness_1 = (await client.get("/api/v1/attendance/crowdedness", headers=headers[0])).json()
    crowdedness_11 = (await client.get("/api/v1/attendance/crowdedness", headers=headers[1])).json()
    assert (crowdedness_1["gym_id"], crowdedness_1["active_count"]) == (str(DISTRICT_1_GYM_ID), 1)
    assert (crowdedness_11["gym_id"], crowdedness_11["active_count"]) == (str(DISTRICT_11_GYM_ID), 1)
    assert json.loads(await redis.get(CrowdednessService.cache_key(DISTRICT_1_GYM_ID)))["active_count"] == 1
    assert json.loads(await redis.get(CrowdednessService.cache_key(DISTRICT_11_GYM_ID)))["active_count"] == 1

    async with sessions() as session:
        stored_sessions = (await session.execute(select(AttendanceSession))).scalars().all()
        stored_events = (await session.execute(select(AttendanceEvent))).scalars().all()
        assert {item.gym_id for item in stored_sessions} == {DISTRICT_1_GYM_ID, DISTRICT_11_GYM_ID}
        assert {item.gym_id for item in stored_events} == {DISTRICT_1_GYM_ID, DISTRICT_11_GYM_ID}

    wrong_checkout = await client.post(
        "/api/v1/attendance/check-out",
        headers=scanner_headers,
        json={"device_id": "isolation-door-11", "qr_token": district_1_token},
    )
    assert wrong_checkout.status_code == 403
    assert wrong_checkout.json()["error"]["code"] == "ATTENDANCE_GYM_MISMATCH"

    checked_out = await client.post(
        "/api/v1/attendance/check-out",
        headers=scanner_headers,
        json={"device_id": "isolation-door-1", "qr_token": district_1_token},
    )
    assert checked_out.status_code == 200
    assert checked_out.json()["occupancy"]["active_count"] == 0
    assert (await client.get("/api/v1/attendance/crowdedness", headers=headers[1])).json()["active_count"] == 1

    forbidden = await client.get(
        f"/api/v1/gyms/{DISTRICT_11_GYM_ID}/crowdedness",
        headers=headers[0],
    )
    assert forbidden.status_code == 403


async def test_manager_history_and_manual_close_are_limited_to_assigned_gym(
    client,
    storage,
    eligible_members,
):
    sessions, _ = storage
    users, _ = eligible_members
    manager = User(
        name="District 1 Manager",
        email="attendance-manager-dist1@example.com",
        password_hash="unused",
        role="manager",
        is_email_verified=True,
    )
    now = datetime.now(UTC)
    district_1_session = AttendanceSession(
        gym_id=DISTRICT_1_GYM_ID,
        user_id=users[0].id,
        checked_in_at=now,
        status="active",
        source="iot_scanner",
    )
    district_11_session = AttendanceSession(
        gym_id=DISTRICT_11_GYM_ID,
        user_id=users[1].id,
        checked_in_at=now,
        status="active",
        source="iot_scanner",
    )
    async with sessions() as session:
        session.add_all([manager, district_1_session, district_11_session])
        await session.flush()
        session.add(
            WorkforceGymAssignment(
                user_id=manager.id,
                gym_id=DISTRICT_1_GYM_ID,
                assigned_role="manager",
            ),
        )
        await session.commit()

    token, _ = create_access_token(user_id=manager.id, role="manager", tier="normal")
    manager_headers = {"Authorization": f"Bearer {token}"}
    history = await client.get("/api/v1/attendance/admin", headers=manager_headers)
    assert history.status_code == 200
    assert [item["gym_id"] for item in history.json()["items"]] == [str(DISTRICT_1_GYM_ID)]

    forbidden_history = await client.get(
        f"/api/v1/attendance/admin?gym_id={DISTRICT_11_GYM_ID}",
        headers=manager_headers,
    )
    assert forbidden_history.status_code == 403
    forbidden_close = await client.post(
        f"/api/v1/attendance/admin/{district_11_session.id}/manual-close",
        headers=manager_headers,
        json={"reason": "Attempting a cross-branch manual closure."},
    )
    assert forbidden_close.status_code == 403

    allowed_close = await client.post(
        f"/api/v1/attendance/admin/{district_1_session.id}/manual-close",
        headers=manager_headers,
        json={"reason": "Member requested help at the District 1 desk."},
    )
    assert allowed_close.status_code == 200
    assert allowed_close.json()["gym_id"] == str(DISTRICT_1_GYM_ID)


async def test_timeout_reconciliation_publishes_one_occupancy_update_per_gym(
    storage,
    eligible_members,
    monkeypatch,
):
    sessions, redis = storage
    users, _ = eligible_members
    now = datetime.now(UTC)
    async with sessions() as session:
        session.add_all(
            [
                AttendanceSession(
                    gym_id=DISTRICT_1_GYM_ID,
                    user_id=users[0].id,
                    checked_in_at=now - timedelta(hours=4),
                    status="active",
                    source="iot_scanner",
                ),
                AttendanceSession(
                    gym_id=DISTRICT_11_GYM_ID,
                    user_id=users[1].id,
                    checked_in_at=now - timedelta(hours=4),
                    status="active",
                    source="iot_scanner",
                ),
            ],
        )
        await session.commit()

    published = []

    async def capture_transition(_publisher, **payload):
        published.append((payload["gym_id"], payload["include_occupancy"], payload["occupancy"].active_count))

    monkeypatch.setattr(AttendanceRealtimePublisher, "publish_transition", capture_transition)
    assert await asyncio.to_thread(close_timed_out_attendance.run) == 2
    assert set(published) == {
        (DISTRICT_1_GYM_ID, True, 0),
        (DISTRICT_11_GYM_ID, True, 0),
    }
    assert json.loads(await redis.get(CrowdednessService.cache_key(DISTRICT_1_GYM_ID)))["active_count"] == 0
    assert json.loads(await redis.get(CrowdednessService.cache_key(DISTRICT_11_GYM_ID)))["active_count"] == 0
