import asyncio
from datetime import UTC, date, datetime, timedelta

import pytest
from jose import jwt
from redis.exceptions import RedisError
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.attendance import AttendanceEvent, AttendanceSession, IoTDevice
from app.models.membership import UserMembership
from app.models.user import User
from app.services.attendance_service import CrowdednessService
from app.services.attendance_realtime_service import AttendanceRealtimePublisher
from app.utils.security import create_access_token, hash_token
from app.workers.celery_app import close_timed_out_attendance

pytestmark = pytest.mark.asyncio


async def test_rotating_qr_concurrent_scans_checkout_and_reconciliation(client, storage, eligible_members, monkeypatch):
    sessions, redis = storage
    users, headers = eligible_members
    published = []

    async def capture_transition(_publisher, **payload):
        async with sessions() as verification_session:
            stored_status = (
                await verification_session.execute(
                    select(AttendanceSession.status).where(AttendanceSession.id == payload["session_id"]),
                )
            ).scalar_one()
        published.append((payload["action"], stored_status))

    monkeypatch.setattr(AttendanceRealtimePublisher, "publish_transition", capture_transition)
    async with sessions() as session:
        session.add_all([IoTDevice(device_id=f"door-{i}", display_name=f"Door {i}", api_key_hash=hash_token("integration-key")) for i in range(2)])
        await session.commit()
    previous = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).json()["token"]
    current = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).json()["token"]
    scanner_headers = {"X-Device-Api-Key": "integration-key"}
    verified = await client.post(
        "/api/v1/attendance/device/verify",
        headers=scanner_headers,
        json={"device_id": "door-0"},
    )
    assert verified.status_code == 200
    assert verified.json() == {"device_id": "door-0", "display_name": "Door 0", "status": "active"}
    obsolete = await client.post("/api/v1/attendance/check-in", headers=scanner_headers, json={"device_id": "door-0", "qr_token": previous})
    assert obsolete.status_code == 409 and obsolete.json()["error"]["code"] == "SUPERSEDED_TOKEN"
    # The actual QR issued by the API must not authorize account access.
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {current}"})).status_code == 401
    responses = await asyncio.gather(*[
        client.post("/api/v1/attendance/check-in", headers=scanner_headers, json={"device_id": f"door-{i}", "qr_token": current}) for i in range(2)
    ])
    assert sorted(response.status_code for response in responses) == [200, 409]
    accepted = next(response.json() for response in responses if response.status_code == 200)
    assert accepted["code"] == "CHECK_IN_SUCCESS"
    assert accepted["message"] == "Check-in recorded."
    assert accepted["session_id"]
    assert accepted["member_id"] == str(users[0].id)
    assert accepted["occurred_at"]
    assert accepted["occupancy"]["active_count"] == 1
    assert accepted["action"] == "check_in"
    assert accepted["attendance_status"] == "active"
    assert accepted["member"]["display_name"] == users[0].name
    assert accepted["member"]["membership_status"] == "active"
    async with sessions() as session:
        assert (await session.execute(select(func.count(AttendanceSession.id)))).scalar_one() == 1
        assert (await session.execute(select(func.count(AttendanceEvent.id)))).scalar_one() == 1
    await redis.delete(CrowdednessService.CACHE_KEY)
    assert (await client.get("/api/v1/attendance/crowdedness", headers=headers[0])).json()["active_count"] == 1
    assert (await client.get("/api/v1/attendance/me", headers=headers[1])).json()["items"] == []
    payload = {"device_id": "door-0", "qr_token": current}
    responses = await asyncio.gather(*[client.post("/api/v1/attendance/check-out", headers=scanner_headers, json=payload) for _ in range(2)])
    assert sorted(response.status_code for response in responses) == [200, 409]
    checked_out = next(response.json() for response in responses if response.status_code == 200)
    assert checked_out["action"] == "check_out"
    assert checked_out["attendance_status"] == "checked_out"
    assert checked_out["member"] == {"display_name": users[0].name, "membership_status": "active"}
    serialized = str(checked_out)
    assert users[0].email not in serialized
    assert users[0].phone not in serialized
    assert "integration-key" not in serialized
    assert current not in serialized
    assert (await client.get("/api/v1/attendance/crowdedness", headers=headers[0])).json()["active_count"] == 0
    async with sessions() as session:
        events = (await session.execute(select(AttendanceEvent.event_type))).scalars().all()
        assert sorted(events) == ["check_in", "check_out"]
    assert published == [("check_in", "active"), ("check_out", "checked_out")]


async def test_scanner_returns_stable_membership_duplicate_and_session_errors(client, storage, eligible_members):
    sessions, _ = storage
    users, headers = eligible_members
    scanner_headers = {"X-Device-Api-Key": "integration-key"}
    async with sessions() as session:
        session.add(IoTDevice(device_id="stable-errors-door", display_name="Stable errors door", api_key_hash=hash_token("integration-key")))
        await session.commit()

    first_token = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).json()["token"]
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == users[0].id))).scalar_one()
        membership.status = "frozen"
        membership.frozen_from = date.today()
        membership.frozen_until = date.today() + timedelta(days=1)
        await session.commit()
    denied = await client.post(
        "/api/v1/attendance/check-in",
        headers=scanner_headers,
        json={"device_id": "stable-errors-door", "qr_token": first_token},
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "INACTIVE_MEMBERSHIP"

    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == users[0].id))).scalar_one()
        membership.status = "active"
        membership.frozen_from = None
        membership.frozen_until = None
        await session.commit()
    accepted = await client.post(
        "/api/v1/attendance/check-in",
        headers=scanner_headers,
        json={"device_id": "stable-errors-door", "qr_token": first_token},
    )
    assert accepted.status_code == 200

    duplicate = await client.post(
        "/api/v1/attendance/check-in",
        headers=scanner_headers,
        json={"device_id": "stable-errors-door", "qr_token": first_token},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_SCAN"

    newer_token = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).json()["token"]
    already_active = await client.post(
        "/api/v1/attendance/check-in",
        headers=scanner_headers,
        json={"device_id": "stable-errors-door", "qr_token": newer_token},
    )
    assert already_active.status_code == 409
    assert already_active.json()["error"]["code"] == "ACTIVE_SESSION_EXISTS"

    second_member_token = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[1])).json()["token"]
    no_session = await client.post(
        "/api/v1/attendance/check-out",
        headers=scanner_headers,
        json={"device_id": "stable-errors-door", "qr_token": second_member_token},
    )
    assert no_session.status_code == 409
    assert no_session.json()["error"]["code"] == "NO_ACTIVE_SESSION"


async def test_realtime_publish_failure_does_not_undo_committed_check_in(client, storage, eligible_members, monkeypatch, caplog):
    sessions, redis = storage
    _, headers = eligible_members
    async with sessions() as session:
        session.add(IoTDevice(device_id="publish-failure-door", display_name="Publish failure door", api_key_hash=hash_token("integration-key")))
        await session.commit()
    token = (await client.get("/api/v1/attendance/qr-token/me", headers=headers[0])).json()["token"]
    secret = "sensitive-publish-exception-material"

    async def fail_publish(*_args, **_kwargs):
        raise RedisError(secret)

    monkeypatch.setattr(redis, "publish", fail_publish)
    response = await client.post(
        "/api/v1/attendance/check-in",
        headers={"X-Device-Api-Key": "integration-key"},
        json={"device_id": "publish-failure-door", "qr_token": token},
    )

    assert response.status_code == 200
    async with sessions() as session:
        assert (await session.execute(select(func.count(AttendanceSession.id)))).scalar_one() == 1
        assert (await session.execute(select(func.count(AttendanceEvent.id)))).scalar_one() == 1
    assert "attendance_realtime_publish_failed" in caplog.text
    assert secret not in caplog.text


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
async def test_membership_restrictions_apply_to_qr_but_not_independent_class_sales(client, storage, eligible_members, state):
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
    # Class sales are independent of membership; an unknown class is therefore still a 404.
    expected = 403 if state == "pending_verification" else 404
    assert (await client.post(f"/api/v1/classes/{users[0].id}/book", headers=headers[0])).status_code == expected


async def test_real_timeout_task_is_repeatable_and_rebuilds_occupancy(client, storage, eligible_members, monkeypatch):
    sessions, redis = storage
    users, headers = eligible_members
    now = datetime.now(UTC)
    published = []

    async def capture_transition(_publisher, **payload):
        published.append((payload["action"], payload["include_occupancy"]))

    monkeypatch.setattr(AttendanceRealtimePublisher, "publish_transition", capture_transition)
    async with sessions() as session:
        session.add_all([
            AttendanceSession(user_id=users[0].id, checked_in_at=now - timedelta(hours=4), status="active", source="iot_scanner"),
            AttendanceSession(user_id=users[1].id, checked_in_at=now - timedelta(hours=4), status="active", source="iot_scanner"),
        ])
        await session.commit()
    # Run the Celery task's real synchronous entry point with its own event loop.
    assert await asyncio.to_thread(close_timed_out_attendance.run) == 2
    assert await asyncio.to_thread(close_timed_out_attendance.run) == 0
    await redis.delete(CrowdednessService.CACHE_KEY)
    assert (await client.get("/api/v1/attendance/crowdedness", headers=headers[0])).json()["active_count"] == 0
    async with sessions() as session:
        assert (await session.execute(select(func.count(AttendanceEvent.id)).where(AttendanceEvent.event_type == "timeout"))).scalar_one() == 2
    assert published == [("timeout", False), ("timeout", True)]


async def test_manual_close_commits_audit_and_publishes_invalidation(client, storage, eligible_members, monkeypatch):
    sessions, _ = storage
    users, _ = eligible_members
    now = datetime.now(UTC)
    staff = User(name="Attendance Staff", email="attendance-staff@example.com", password_hash="unused", role="staff", is_email_verified=True)
    attendance_session = AttendanceSession(user_id=users[0].id, checked_in_at=now, status="active", source="iot_scanner")
    async with sessions() as session:
        session.add_all([staff, attendance_session])
        await session.commit()
    published = []

    async def capture_transition(_publisher, **payload):
        async with sessions() as verification_session:
            stored = await verification_session.get(AttendanceSession, payload["session_id"])
            assert stored.status == "manual_closed"
        published.append(payload["action"])

    monkeypatch.setattr(AttendanceRealtimePublisher, "publish_transition", capture_transition)
    token, _ = create_access_token(user_id=staff.id, role="staff", tier="normal")
    response = await client.post(
        f"/api/v1/attendance/admin/{attendance_session.id}/manual-close",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Member requested assistance at the front desk."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "manual_closed"
    assert published == ["manual_close"]
