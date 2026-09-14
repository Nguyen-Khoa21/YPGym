import asyncio
from datetime import UTC, date, datetime, timedelta

import pytest
from jose import jwt
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.attendance import AttendanceEvent, AttendanceSession, IoTDevice
from app.models.membership import UserMembership
from app.services.attendance_service import CrowdednessService
from app.utils.security import hash_token
from app.workers.celery_app import close_timed_out_attendance

pytestmark = pytest.mark.asyncio


async def test_rotating_qr_concurrent_scans_checkout_and_reconciliation(client, storage, eligible_members):
    sessions, redis = storage
    users, headers = eligible_members
    async with sessions() as session:
        session.add_all([IoTDevice(device_id=f"door-{i}", display_name=f"Door {i}", api_key_hash=hash_token("integration-key")) for i in range(2)])
        await session.commit()
    previous = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).json()["token"]
    current = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).json()["token"]
    scanner_headers = {"X-Device-Api-Key": "integration-key"}
    obsolete = await client.post("/api/v1/attendance/check-in", headers=scanner_headers, json={"device_id": "door-0", "qr_token": previous})
    assert obsolete.status_code == 409 and obsolete.json()["error"]["code"] == "SUPERSEDED_TOKEN"
    # The actual QR issued by the API must not authorize account access.
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {current}"})).status_code == 401
    responses = await asyncio.gather(*[
        client.post("/api/v1/attendance/check-in", headers=scanner_headers, json={"device_id": f"door-{i}", "qr_token": current}) for i in range(2)
    ])
    assert sorted(response.status_code for response in responses) == [200, 409]
    async with sessions() as session:
        assert (await session.execute(select(func.count(AttendanceSession.id)))).scalar_one() == 1
        assert (await session.execute(select(func.count(AttendanceEvent.id)))).scalar_one() == 1
    await redis.delete(CrowdednessService.CACHE_KEY)
    assert (await client.get("/api/v1/attendance/crowdedness", headers=headers[0])).json()["active_count"] == 1
    assert (await client.get("/api/v1/attendance/me", headers=headers[1])).json()["items"] == []
    payload = {"device_id": "door-0", "qr_token": current}
    responses = await asyncio.gather(*[client.post("/api/v1/attendance/check-out", headers=scanner_headers, json=payload) for _ in range(2)])
    assert sorted(response.status_code for response in responses) == [200, 409]
    assert (await client.get("/api/v1/attendance/crowdedness", headers=headers[0])).json()["active_count"] == 0
    async with sessions() as session:
        events = (await session.execute(select(AttendanceEvent.event_type))).scalars().all()
        assert sorted(events) == ["check_in", "check_out"]


async def test_expired_and_malformed_qr_rejected(client, storage, eligible_members):
    sessions, _ = storage
    users, headers = eligible_members
    settings = get_settings()
    async with sessions() as session:
        session.add(IoTDevice(device_id="door", display_name="Door", api_key_hash=hash_token("integration-key")))
        await session.commit()
    token = jwt.encode({"sub": str(users[0].id), "jti": "expired", "type": "attendance_qr", "exp": datetime.now(UTC) - timedelta(seconds=1)}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    for qr, code in [(token, "EXPIRED_TOKEN"), ("malformed-qr-material", "INVALID_TOKEN"), (headers[0]["Authorization"].removeprefix("Bearer "), "INVALID_TOKEN")]:
        response = await client.post("/api/v1/attendance/check-in", headers={"X-Device-Api-Key": "integration-key"}, json={"device_id": "door", "qr_token": qr})
        assert response.status_code == 400 and response.json()["error"]["code"] == code


@pytest.mark.parametrize("state", ["frozen", "expired", "revoked", "cancelled", "pending_verification"])
async def test_membership_restrictions_apply_to_qr_and_booking(client, storage, eligible_members, state):
    sessions, _ = storage
    users, headers = eligible_members
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == users[0].id))).scalar_one()
        membership.status = state
        if state == "frozen":
            membership.frozen_from, membership.frozen_until = date.today(), date.today() + timedelta(days=1)
        if state == "expired":
            membership.expiry_date = date.today() - timedelta(days=1)
        if state == "pending_verification":
            user = await session.get(type(users[0]), users[0].id)
            user.is_email_verified = False
        await session.commit()
    assert (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).status_code == 403
    # Eligibility is checked before class lookup, including an unknown class.
    assert (await client.post(f"/api/v1/classes/{users[0].id}/book", headers=headers[0])).status_code == 403


async def test_real_timeout_task_is_repeatable_and_rebuilds_occupancy(client, storage, eligible_members):
    sessions, redis = storage
    users, headers = eligible_members
    now = datetime.now(UTC)
    async with sessions() as session:
        session.add_all([
            AttendanceSession(user_id=users[0].id, checked_in_at=now - timedelta(hours=4), status="active", source="iot_scanner"),
            AttendanceSession(user_id=users[1].id, checked_in_at=now, status="active", source="iot_scanner"),
        ])
        await session.commit()
    # Run the Celery task's real synchronous entry point with its own event loop.
    assert await asyncio.to_thread(close_timed_out_attendance.run) == 1
    assert await asyncio.to_thread(close_timed_out_attendance.run) == 0
    await redis.delete(CrowdednessService.CACHE_KEY)
    assert (await client.get("/api/v1/attendance/crowdedness", headers=headers[0])).json()["active_count"] == 1
    async with sessions() as session:
        assert (await session.execute(select(func.count(AttendanceEvent.id)).where(AttendanceEvent.event_type == "timeout"))).scalar_one() == 1
