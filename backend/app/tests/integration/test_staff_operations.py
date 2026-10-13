import asyncio
import re
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.models.classes import PersonalTrainer
from app.models.operations import AuditLog
from app.models.staff import StaffShift
from app.models.user import User
from app.utils.security import create_access_token, hash_password, verify_password

pytestmark = pytest.mark.asyncio


def auth_header(user: User) -> dict[str, str]:
    token = create_access_token(user_id=user.id, role=user.role, tier=user.tier)[0]
    return {"Authorization": f"Bearer {token}"}


async def seed_roles(storage):
    sessions, _ = storage
    async with sessions() as session:
        manager = User(
            name="Workforce Manager",
            email="workforce-manager@example.com",
            phone="6600010001",
            password_hash=hash_password("ManagerPass123!"),
            role="manager",
            is_email_verified=True,
        )
        member = User(
            name="Ordinary Member",
            email="workforce-member@example.com",
            phone="6600010002",
            password_hash=hash_password("MemberPass123!"),
            role="member",
            is_email_verified=True,
        )
        session.add_all([manager, member])
        await session.commit()
        return manager, member


async def create_account(client, manager: User, *, login_name: str, role: str = "staff"):
    response = await client.post(
        "/api/v1/admin/staff-accounts",
        headers=auth_header(manager),
        json={"name": f"{role.title()} Operator", "login_name": login_name, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_manager_provisions_distinct_accounts_and_first_login_password_is_enforced(client, storage):
    manager, member = await seed_roles(storage)
    denied = await client.post(
        "/api/v1/admin/staff-accounts",
        headers=auth_header(member),
        json={"name": "Denied Staff", "login_name": "denied.staff", "role": "staff"},
    )
    assert denied.status_code == 403
    escalation = await client.post(
        "/api/v1/admin/staff-accounts",
        headers=auth_header(manager),
        json={"name": "Not Admin", "login_name": "not.admin", "role": "admin"},
    )
    assert escalation.status_code == 422

    result = await create_account(client, manager, login_name="alex.operator")
    password = result["temporary_password"]
    assert result["account"]["email"] == "alex.operator@ypgym.dev"
    assert result["account"]["must_change_password"] is True
    assert len(password) == 20
    assert all(re.search(pattern, password) for pattern in (r"[A-Z]", r"[a-z]", r"[0-9]", r"[^A-Za-z0-9]"))

    pt_result = await create_account(client, manager, login_name="jamie.coach", role="pt")
    assert pt_result["account"]["trainer_profile_id"]
    duplicate = await client.post(
        "/api/v1/admin/staff-accounts",
        headers=auth_header(manager),
        json={"name": "Duplicate", "login_name": "alex.operator", "role": "staff"},
    )
    assert duplicate.status_code == 409

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": result["account"]["email"], "password": password},
    )
    assert login.status_code == 200
    login_json = login.json()
    assert login_json["user"]["must_change_password"] is True
    staff_headers = {"Authorization": f"Bearer {login_json['access_token']}"}
    blocked = await client.get("/api/v1/staff/shifts/me", headers=staff_headers)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"
    changed = await client.patch(
        "/api/v1/users/me",
        headers=staff_headers,
        json={"current_password": password, "new_password": "PrivatePass456!"},
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False

    listed = await client.get("/api/v1/admin/staff-accounts", headers=auth_header(manager))
    assert listed.status_code == 200
    serialized = listed.text
    assert password not in serialized and "password_hash" not in serialized
    assert listed.json()["page"]["total"] == 2
    async with storage[0]() as session:
        staff = (await session.execute(select(User).where(User.email == "alex.operator@ypgym.dev"))).scalar_one()
        assert verify_password("PrivatePass456!", staff.password_hash)
        assert not verify_password(password, staff.password_hash)
        assert await session.scalar(select(func.count(PersonalTrainer.id)).where(PersonalTrainer.user_id.is_not(None))) == 1
        audit = (await session.execute(select(AuditLog).where(AuditLog.action == "staff_account.created"))).scalars().all()
        assert len(audit) == 2
        assert password not in str([item.after_data for item in audit])


async def test_staff_time_clock_is_owned_serialized_and_manager_reported(client, storage):
    manager, member = await seed_roles(storage)
    created = await create_account(client, manager, login_name="shift.operator")
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": created["account"]["email"], "password": created["temporary_password"]},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"current_password": created["temporary_password"], "new_password": "ShiftPrivate456!"},
    )

    attempts = await asyncio.gather(
        client.post("/api/v1/staff/shifts/clock-in", headers=headers),
        client.post("/api/v1/staff/shifts/clock-in", headers=headers),
    )
    assert sorted(response.status_code for response in attempts) == [201, 409]
    own = await client.get("/api/v1/staff/shifts/me", headers=headers)
    assert own.status_code == 200
    assert own.json()["open_shift"]["user_id"] == created["account"]["id"]
    assert own.json()["gym_timezone"] == "Asia/Ho_Chi_Minh"
    assert (await client.get("/api/v1/staff/shifts/me", headers=auth_header(member))).status_code == 403

    local_day = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat()
    report = await client.get(
        "/api/v1/admin/staff-shifts",
        headers=auth_header(manager),
        params={"status": "open", "date_from": local_day, "date_to": local_day},
    )
    assert report.status_code == 200
    assert report.json()["page"]["total"] == 1
    assert report.json()["items"][0]["staff_email"] == created["account"]["email"]
    invalid_range = await client.get(
        "/api/v1/admin/staff-shifts",
        headers=auth_header(manager),
        params={"date_from": "2026-10-14", "date_to": "2026-10-13"},
    )
    assert invalid_range.status_code == 422

    closed = await client.post("/api/v1/staff/shifts/clock-out", headers=headers)
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert (await client.post("/api/v1/staff/shifts/clock-out", headers=headers)).status_code == 409
    async with storage[0]() as session:
        session.add(
            StaffShift(
                user_id=UUID(created["account"]["id"]),
                clocked_in_at=datetime(2026, 10, 12, 16, 30, tzinfo=UTC),
                clocked_out_at=datetime(2026, 10, 12, 18, 30, tzinfo=UTC),
            ),
        )
        await session.commit()
        shifts = (await session.execute(select(StaffShift))).scalars().all()
        assert len(shifts) == 2 and all(shift.clocked_out_at is not None for shift in shifts)
        actions = set((await session.execute(select(AuditLog.action))).scalars().all())
        assert {"staff_shift.clocked_in", "staff_shift.clocked_out"}.issubset(actions)

    cross_midnight = await client.get(
        "/api/v1/admin/staff-shifts",
        headers=auth_header(manager),
        params={"date_from": "2026-10-12", "date_to": "2026-10-12"},
    )
    assert cross_midnight.status_code == 200
    assert cross_midnight.json()["page"]["total"] == 1
    assert cross_midnight.json()["items"][0]["duration_minutes"] == 120
