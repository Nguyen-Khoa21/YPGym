from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.exceptions import PermissionDeniedError
from app.models.gym import (
    DISTRICT_1_GYM_ID,
    DISTRICT_11_GYM_ID,
    GymLocation,
    WorkforceGymAssignment,
)
from app.models.membership import MembershipPlan, UserMembership
from app.models.operations import AuditLog
from app.models.user import User
from app.services.gym_service import GymScopeService
from app.utils.security import create_access_token


pytestmark = pytest.mark.asyncio


def auth_header(user: User) -> dict[str, str]:
    token = create_access_token(user_id=user.id, role=user.role, tier=user.tier)[0]
    return {"Authorization": f"Bearer {token}"}


async def test_public_locations_and_admin_management_are_role_safe(client, storage):
    sessions, _ = storage
    async with sessions() as session:
        admin = User(name="Owner", email="owner-locations@example.com", role="admin", password_hash="unused")
        manager = User(name="Manager", email="manager-locations@example.com", role="manager", password_hash="unused")
        session.add_all([admin, manager])
        await session.commit()

    public = await client.get("/api/v1/gyms")
    assert public.status_code == 200
    assert {item["slug"] for item in public.json()} == {"district-1", "district-11"}
    assert (await client.get(f"/api/v1/gyms/{DISTRICT_1_GYM_ID}")).status_code == 200
    assert (await client.get("/api/v1/admin/gym-locations", headers=auth_header(manager))).status_code == 403
    missing_gym = await client.post(
        "/api/v1/admin/staff-accounts",
        headers=auth_header(admin),
        json={"name": "Unassigned Staff", "login_name": "unassigned.staff", "role": "staff"},
    )
    assert missing_gym.status_code == 422
    assigned_account = await client.post(
        "/api/v1/admin/staff-accounts",
        headers=auth_header(admin),
        json={
            "name": "District 11 Staff",
            "login_name": "district11.staff",
            "role": "staff",
            "gym_id": str(DISTRICT_11_GYM_ID),
        },
    )
    assert assigned_account.status_code == 201, assigned_account.text

    created = await client.post(
        "/api/v1/admin/gym-locations",
        headers=auth_header(admin),
        json={
            "name": "YPGym District 5",
            "slug": "district-5",
            "district": "District 5",
            "address": "District 5, Ho Chi Minh City",
            "timezone": "Asia/Ho_Chi_Minh",
            "capacity": 120,
        },
    )
    assert created.status_code == 201, created.text
    gym_id = created.json()["id"]
    assert (await client.post(
        "/api/v1/admin/gym-locations",
        headers=auth_header(admin),
        json={**created.json(), "id": None},
    )).status_code == 409
    deactivated = await client.patch(
        f"/api/v1/admin/gym-locations/{gym_id}",
        headers=auth_header(admin),
        json={"is_active": False},
    )
    assert deactivated.status_code == 200 and deactivated.json()["is_active"] is False
    assert (await client.get(f"/api/v1/gyms/{gym_id}")).status_code == 404
    async with sessions() as session:
        audits = await session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.entity_type == "gym_location")
        )
        assert audits == 2


async def test_workforce_and_member_scope_cannot_cross_locations(client, storage):
    sessions, _ = storage
    today = date.today()
    async with sessions() as session:
        admin = User(name="Owner", email="scope-owner@example.com", role="admin", password_hash="unused")
        manager = User(name="D1 Manager", email="scope-manager@example.com", role="manager", password_hash="unused")
        staff = User(name="D11 Staff", email="scope-staff@example.com", role="staff", password_hash="unused")
        member = User(name="D1 Member", email="scope-member@example.com", role="member", password_hash="unused")
        plan = MembershipPlan(
            name="Scope plan",
            duration_months=1,
            duration_days=30,
            base_price=Decimal("720000"),
        )
        session.add_all([admin, manager, staff, member, plan])
        await session.flush()
        session.add_all(
            [
                WorkforceGymAssignment(
                    user_id=manager.id,
                    gym_id=DISTRICT_1_GYM_ID,
                    assigned_role="manager",
                ),
                UserMembership(
                    user_id=member.id,
                    plan_id=plan.id,
                    home_gym_id=DISTRICT_1_GYM_ID,
                    status="active",
                    start_date=today,
                    expiry_date=today + timedelta(days=30),
                ),
            ]
        )
        await session.commit()

    assignment = await client.put(
        "/api/v1/admin/gym-locations/workforce/assignments",
        headers=auth_header(admin),
        json={"user_id": str(staff.id), "gym_id": str(DISTRICT_11_GYM_ID)},
    )
    assert assignment.status_code == 200, assignment.text
    assert assignment.json()["gym_id"] == str(DISTRICT_11_GYM_ID)
    assert (await client.put(
        "/api/v1/admin/gym-locations/workforce/assignments",
        headers=auth_header(manager),
        json={"user_id": str(staff.id), "gym_id": str(DISTRICT_1_GYM_ID)},
    )).status_code == 403

    async with sessions() as session:
        assert await GymScopeService(session).effective_gym_id(user=manager) == DISTRICT_1_GYM_ID
        assert await GymScopeService(session).effective_gym_id(user=staff) == DISTRICT_11_GYM_ID
        assert await GymScopeService(session).effective_gym_id(user=member) == DISTRICT_1_GYM_ID
        with pytest.raises(PermissionDeniedError):
            await GymScopeService(session).require_access(user=manager, requested_gym_id=DISTRICT_11_GYM_ID)
        assert (
            await GymScopeService(session).require_access(user=admin, requested_gym_id=DISTRICT_11_GYM_ID)
        ).id == DISTRICT_11_GYM_ID
        active_staff_assignments = await session.scalar(
            select(func.count())
            .select_from(WorkforceGymAssignment)
            .where(
                WorkforceGymAssignment.user_id == staff.id,
                WorkforceGymAssignment.is_active.is_(True),
            )
        )
        assert active_staff_assignments == 1


async def test_location_columns_are_required_and_legacy_defaults_are_district_one(storage):
    sessions, _ = storage
    async with sessions() as session:
        locations = (await session.scalars(select(GymLocation))).all()
        assert {item.id for item in locations} == {DISTRICT_1_GYM_ID, DISTRICT_11_GYM_ID}
