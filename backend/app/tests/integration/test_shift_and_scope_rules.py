from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.attendance import AttendanceEvent, AttendanceSession
from app.models.gym import DISTRICT_1_GYM_ID, DISTRICT_11_GYM_ID, WorkforceGymAssignment
from app.models.operations import AuditLog
from app.models.user import User
from app.utils.security import create_access_token

pytestmark = pytest.mark.asyncio


async def make_user(storage, role: str, gym_id=None) -> dict[str, str]:
    sessions, _ = storage
    user = User(
        name=f"{role} scope test",
        email=f"{role}-{uuid4().hex[:8]}@example.com",
        password_hash="unused",
        role=role,
        is_email_verified=True,
    )
    async with sessions() as session:
        session.add(user)
        await session.flush()
        if gym_id is not None:
            session.add(WorkforceGymAssignment(user_id=user.id, gym_id=gym_id, assigned_role=role))
        await session.commit()
    token, _ = create_access_token(user_id=user.id, role=role, tier="normal")
    return {"Authorization": f"Bearer {token}"}


def bearer(headers: dict[str, str]) -> dict[str, str]:
    return {"Authorization": headers["Authorization"]}


async def add_active_sessions(storage, members):
    sessions, _ = storage
    now = datetime.now(UTC)
    d1 = AttendanceSession(gym_id=DISTRICT_1_GYM_ID, user_id=members[0].id, checked_in_at=now, status="active", source="iot_scanner")
    d11 = AttendanceSession(gym_id=DISTRICT_11_GYM_ID, user_id=members[1].id, checked_in_at=now, status="active", source="iot_scanner")
    async with sessions() as session:
        session.add_all([d1, d11])
        await session.commit()
    return d1, d11


async def test_staff_attendance_requires_an_open_shift_at_the_assigned_gym(client, storage, eligible_members):
    members, _ = eligible_members
    d1_session, d11_session = await add_active_sessions(storage, members)
    staff = await make_user(storage, "staff", DISTRICT_1_GYM_ID)
    headers = bearer(staff)
    close_body = {"reason": "Member forgot to scan out at the desk."}

    locked = await client.get("/api/v1/attendance/admin", headers=headers)
    assert locked.status_code == 403
    assert locked.json()["error"]["code"] == "SHIFT_REQUIRED"
    locked_close = await client.post(f"/api/v1/attendance/admin/{d1_session.id}/manual-close", headers=headers, json=close_body)
    assert locked_close.status_code == 403
    assert locked_close.json()["error"]["code"] == "SHIFT_REQUIRED"

    assert (await client.post("/api/v1/staff/shifts/clock-in", headers=headers)).status_code == 201
    listing = await client.get("/api/v1/attendance/admin", headers=headers)
    assert listing.status_code == 200
    assert {item["gym_id"] for item in listing.json()["items"]} == {str(DISTRICT_1_GYM_ID)}
    other_gym = await client.get(f"/api/v1/attendance/admin?gym_id={DISTRICT_11_GYM_ID}", headers=headers)
    assert other_gym.status_code == 403

    cross_close = await client.post(f"/api/v1/attendance/admin/{d11_session.id}/manual-close", headers=headers, json=close_body)
    assert cross_close.status_code == 403
    closed = await client.post(f"/api/v1/attendance/admin/{d1_session.id}/manual-close", headers=headers, json=close_body)
    assert closed.status_code == 200
    assert closed.json()["status"] == "manual_closed"
    again = await client.post(f"/api/v1/attendance/admin/{d1_session.id}/manual-close", headers=headers, json=close_body)
    assert again.status_code == 200
    assert again.json()["status"] == "manual_closed"

    sessions, _ = storage
    async with sessions() as session:
        assert await session.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.action == "attendance.manual_closed", AuditLog.entity_id == str(d1_session.id)
            )
        ) == 1
        untouched = await session.get(AttendanceSession, d11_session.id)
        assert untouched.status == "active"

    assert (await client.post("/api/v1/staff/shifts/clock-out", headers=headers)).status_code == 200
    relocked = await client.get("/api/v1/attendance/admin", headers=headers)
    assert relocked.status_code == 403
    assert relocked.json()["error"]["code"] == "SHIFT_REQUIRED"


async def test_shift_at_a_previous_gym_does_not_unlock_the_new_assignment(client, storage):
    staff = await make_user(storage, "staff", DISTRICT_1_GYM_ID)
    headers = bearer(staff)
    assert (await client.post("/api/v1/staff/shifts/clock-in", headers=headers)).status_code == 201
    sessions, _ = storage
    async with sessions() as session:
        assignment = (await session.execute(
            select(WorkforceGymAssignment).where(WorkforceGymAssignment.user_id == User.id, User.email.like("staff-%"))
        )).scalars().first()
        assert assignment is not None
        assignment.gym_id = DISTRICT_11_GYM_ID
        await session.commit()
    response = await client.get("/api/v1/attendance/admin", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SHIFT_REQUIRED"


async def test_manager_and_owner_do_not_need_a_shift(client, storage):
    manager = bearer(await make_user(storage, "manager", DISTRICT_1_GYM_ID))
    owner = bearer(await make_user(storage, "admin"))
    assert (await client.get("/api/v1/attendance/admin", headers=manager)).status_code == 200
    assert (await client.get(f"/api/v1/attendance/admin?gym_id={DISTRICT_11_GYM_ID}", headers=owner)).status_code == 200


async def test_my_gym_returns_the_assigned_or_home_gym_and_owner_must_choose(client, storage, eligible_members):
    _, member_headers = eligible_members
    manager = bearer(await make_user(storage, "manager", DISTRICT_11_GYM_ID))
    staff = bearer(await make_user(storage, "staff", DISTRICT_1_GYM_ID))
    owner = bearer(await make_user(storage, "admin"))
    assert (await client.get("/api/v1/gyms/me", headers=manager)).json()["id"] == str(DISTRICT_11_GYM_ID)
    assert (await client.get("/api/v1/gyms/me", headers=staff)).json()["id"] == str(DISTRICT_1_GYM_ID)
    assert (await client.get("/api/v1/gyms/me", headers=member_headers[0])).json()["id"] == str(DISTRICT_1_GYM_ID)
    owner_response = await client.get("/api/v1/gyms/me", headers=owner)
    assert owner_response.status_code == 422
    assert owner_response.json()["error"]["code"] == "GYM_SCOPE_REQUIRED"
    assert (await client.get("/api/v1/gyms/me")).status_code == 401


async def test_analytics_summary_is_scoped_and_revenue_is_owner_only(client, storage, eligible_members):
    members, _ = eligible_members
    sessions, _ = storage
    now = datetime.now(UTC)
    async with sessions() as session:
        for gym_id, user, count in ((DISTRICT_1_GYM_ID, members[0], 2), (DISTRICT_11_GYM_ID, members[1], 1)):
            for offset in range(count):
                row = AttendanceSession(gym_id=gym_id, user_id=user.id, checked_in_at=now - timedelta(hours=offset + 1), closed_at=now - timedelta(minutes=30), status="checked_out", source="iot_scanner")
                session.add(row)
                await session.flush()
                session.add(AttendanceEvent(gym_id=gym_id, session_id=row.id, user_id=user.id, event_type="check_in", event_at=row.checked_in_at, source="iot_scanner"))
        await session.commit()

    manager = bearer(await make_user(storage, "manager", DISTRICT_1_GYM_ID))
    owner = bearer(await make_user(storage, "admin"))
    url = "/api/v1/admin/analytics/summary"

    mine = (await client.get(url, headers=manager)).json()
    assert mine["gym_id"] == str(DISTRICT_1_GYM_ID)
    assert mine["attendance"]["check_ins"] == 2
    assert mine["revenue"] is None
    assert mine["attendance"]["current_occupancy"]["gym_id"] == str(DISTRICT_1_GYM_ID)
    assert (await client.get(f"{url}?gym_id={DISTRICT_11_GYM_ID}", headers=manager)).status_code == 403

    chain = (await client.get(url, headers=owner)).json()
    assert chain["gym_id"] is None
    assert chain["attendance"]["check_ins"] == 3
    assert chain["revenue"] is not None
    assert chain["attendance"]["current_occupancy"] is None
    district_11 = (await client.get(f"{url}?gym_id={DISTRICT_11_GYM_ID}", headers=owner)).json()
    assert district_11["attendance"]["check_ins"] == 1 and district_11["gym_id"] == str(DISTRICT_11_GYM_ID)

    # A cached owner response must never be served to a manager.
    again = (await client.get(url, headers=manager)).json()
    assert again["revenue"] is None and again["attendance"]["check_ins"] == 2

    for role in ("staff", "pt"):
        assert (await client.get(url, headers=bearer(await make_user(storage, role, DISTRICT_1_GYM_ID)))).status_code == 403


async def test_owner_views_require_an_explicit_gym(client, storage):
    owner = bearer(await make_user(storage, "admin"))
    for path in ("/api/v1/admin/classes", "/api/v1/admin/analytics/peak-hours", "/api/v1/attendance/crowdedness"):
        missing = await client.get(path, headers=owner)
        assert missing.status_code == 422, path
        assert missing.json()["error"]["code"] == "GYM_SCOPE_REQUIRED", path
        chosen = await client.get(f"{path}?gym_id={DISTRICT_11_GYM_ID}", headers=owner)
        assert chosen.status_code == 200, path
