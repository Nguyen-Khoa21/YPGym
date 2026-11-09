"""Package 13: each gym keeps its own manager, staff and PT accounts. Only the owner crosses gyms."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.models.gym import DISTRICT_1_GYM_ID, DISTRICT_11_GYM_ID, WorkforceGymAssignment
from app.models.membership import MembershipPlan, UserMembership
from app.models.operations import AuditLog, MembershipFreezeRequest
from app.models.staff import StaffShift
from app.models.user import User
from app.utils.security import create_access_token


pytestmark = pytest.mark.asyncio


def auth(user: User) -> dict[str, str]:
    token = create_access_token(user_id=user.id, role=user.role, tier=user.tier)[0]
    return {"Authorization": f"Bearer {token}"}


async def person(session, role: str, email: str, gym_id=None) -> User:
    user = User(name=email.split("@")[0], email=email, role=role, password_hash="unused", is_email_verified=True)
    session.add(user)
    await session.flush()
    if gym_id is not None:
        session.add(WorkforceGymAssignment(user_id=user.id, gym_id=gym_id, assigned_role=role))
    return user


@pytest_asyncio.fixture
async def world(storage):
    """Two gyms, each with its own manager, staff and one active member, plus the owner."""
    sessions, _ = storage
    today = date.today()
    async with sessions() as session:
        plan = MembershipPlan(name="Separation plan", duration_months=1, duration_days=30, base_price=Decimal("720000"))
        session.add(plan)
        await session.flush()
        data = {
            "owner": await person(session, "admin", "sep-owner@example.com"),
            "m1": await person(session, "manager", "sep-m1@example.com", DISTRICT_1_GYM_ID),
            "m11": await person(session, "manager", "sep-m11@example.com", DISTRICT_11_GYM_ID),
            "s1": await person(session, "staff", "sep-s1@example.com", DISTRICT_1_GYM_ID),
            "s11": await person(session, "staff", "sep-s11@example.com", DISTRICT_11_GYM_ID),
            "p11": await person(session, "pt", "sep-p11@example.com", DISTRICT_11_GYM_ID),
            "unassigned": await person(session, "staff", "sep-none@example.com"),
            "member1": await person(session, "member", "sep-member1@example.com"),
            "member11": await person(session, "member", "sep-member11@example.com"),
        }
        for key, gym in (("member1", DISTRICT_1_GYM_ID), ("member11", DISTRICT_11_GYM_ID)):
            session.add(UserMembership(user_id=data[key].id, plan_id=plan.id, home_gym_id=gym, status="active", start_date=today, expiry_date=today + timedelta(days=30)))
        await session.commit()
        for user in data.values():
            await session.refresh(user)
    return data


async def test_each_workforce_account_has_exactly_one_active_gym(storage, world):
    sessions, _ = storage
    async with sessions() as session:
        counts = (await session.execute(
            select(WorkforceGymAssignment.user_id, func.count()).where(WorkforceGymAssignment.is_active.is_(True)).group_by(WorkforceGymAssignment.user_id),
        )).all()
    assert counts and all(count == 1 for _, count in counts)


async def test_manager_member_views_are_limited_to_their_gym(client, world):
    listing = await client.get("/api/v1/admin/members", headers=auth(world["m1"]))
    emails = {item["email"] for item in listing.json()["items"]}
    assert "sep-member1@example.com" in emails and "sep-s1@example.com" in emails
    assert not emails & {"sep-member11@example.com", "sep-s11@example.com", "sep-p11@example.com"}
    assert (await client.get("/api/v1/admin/members", params={"gym_id": str(DISTRICT_11_GYM_ID)}, headers=auth(world["m1"]))).status_code == 403
    assert (await client.get(f"/api/v1/admin/members/{world['member1'].id}", headers=auth(world["m1"]))).status_code == 200
    assert (await client.get(f"/api/v1/admin/members/{world['member11'].id}", headers=auth(world["m1"]))).status_code == 403
    assert (await client.get(f"/api/v1/admin/members/{world['s11'].id}", headers=auth(world["m1"]))).status_code == 403


async def test_owner_is_the_only_cross_gym_role(client, world):
    everything = await client.get("/api/v1/admin/members", params={"page_size": 100}, headers=auth(world["owner"]))
    emails = {item["email"] for item in everything.json()["items"]}
    assert {"sep-member1@example.com", "sep-member11@example.com"} <= emails
    only_11 = await client.get("/api/v1/admin/members", params={"gym_id": str(DISTRICT_11_GYM_ID), "page_size": 100}, headers=auth(world["owner"]))
    scoped = {item["email"] for item in only_11.json()["items"]}
    assert "sep-member11@example.com" in scoped and "sep-member1@example.com" not in scoped
    assert (await client.get(f"/api/v1/admin/members/{world['member11'].id}", headers=auth(world["owner"]))).status_code == 200
    # Staff and PT never reach the CRM.
    for key in ("s1", "p11"):
        assert (await client.get("/api/v1/admin/members", headers=auth(world[key]))).status_code == 403


async def test_staff_account_and_shift_lists_and_creation_are_scoped(client, storage, world):
    sessions, _ = storage
    async with sessions() as session:
        session.add_all([
            StaffShift(user_id=world["s1"].id, gym_id=DISTRICT_1_GYM_ID, clocked_in_at=datetime.now(UTC)),
            StaffShift(user_id=world["s11"].id, gym_id=DISTRICT_11_GYM_ID, clocked_in_at=datetime.now(UTC)),
        ])
        await session.commit()
    accounts = (await client.get("/api/v1/admin/staff-accounts", headers=auth(world["m1"]))).json()["items"]
    assert {item["email"] for item in accounts} == {"sep-s1@example.com"}
    assert accounts[0]["gym_id"] == str(DISTRICT_1_GYM_ID) and accounts[0]["gym_name"]
    shifts = (await client.get("/api/v1/admin/staff-shifts", headers=auth(world["m1"]))).json()["items"]
    assert {item["gym_id"] for item in shifts} == {str(DISTRICT_1_GYM_ID)}
    assert (await client.get("/api/v1/admin/staff-accounts", params={"gym_id": str(DISTRICT_11_GYM_ID)}, headers=auth(world["m1"]))).status_code == 403
    owner_all = (await client.get("/api/v1/admin/staff-accounts", headers=auth(world["owner"]))).json()["items"]
    assert {"sep-s1@example.com", "sep-s11@example.com", "sep-p11@example.com"} <= {item["email"] for item in owner_all}

    other_gym = await client.post("/api/v1/admin/staff-accounts", headers=auth(world["m1"]), json={"name": "Cross Gym", "login_name": "cross.gym", "role": "staff", "gym_id": str(DISTRICT_11_GYM_ID)})
    assert other_gym.status_code == 403
    own_gym = await client.post("/api/v1/admin/staff-accounts", headers=auth(world["m1"]), json={"name": "Own Gym", "login_name": "own.gym", "role": "staff"})
    assert own_gym.status_code == 201, own_gym.text
    assert own_gym.json()["account"]["gym_id"] == str(DISTRICT_1_GYM_ID)
    missing_for_owner = await client.post("/api/v1/admin/staff-accounts", headers=auth(world["owner"]), json={"name": "No Gym", "login_name": "no.gym", "role": "staff"})
    assert missing_for_owner.status_code == 422


async def test_membership_requests_cannot_be_read_or_decided_across_gyms(client, storage, world):
    sessions, _ = storage
    today = date.today()
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == world["member11"].id))).scalar_one()
        request = MembershipFreezeRequest(
            user_id=world["member11"].id, membership_id=membership.id, status="pending", reason="Travelling for work next week",
            requested_start_date=today + timedelta(days=1), requested_end_date=today + timedelta(days=8),
        )
        session.add(request)
        await session.commit()
        request_id = request.id
    pending_for_m1 = (await client.get("/api/v1/admin/membership-requests", headers=auth(world["m1"]))).json()["items"]
    assert all(item["user_id"] != str(world["member11"].id) for item in pending_for_m1)
    visible_to_m11 = (await client.get("/api/v1/admin/membership-requests", headers=auth(world["m11"]))).json()["items"]
    assert any(item["user_id"] == str(world["member11"].id) for item in visible_to_m11)
    decision = {"approve": True, "decision_reason": "Approved by the wrong gym"}
    assert (await client.post(f"/api/v1/admin/freeze-requests/{request_id}/decision", headers=auth(world["m1"]), json=decision)).status_code == 403
    async with sessions() as session:
        assert (await session.get(MembershipFreezeRequest, request_id)).status == "pending"
    assert (await client.post(f"/api/v1/admin/freeze-requests/{request_id}/decision", headers=auth(world["m11"]), json={**decision, "decision_reason": "Approved by the right gym"})).status_code == 200


async def test_unassigned_workforce_accounts_are_refused_with_a_clear_code(client, world):
    response = await client.get("/api/v1/gyms/me", headers=auth(world["unassigned"]))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "GYM_ASSIGNMENT_REQUIRED"


async def test_only_the_owner_moves_accounts_and_the_move_is_audited(client, storage, world):
    sessions, _ = storage
    body = {"user_id": str(world["s1"].id), "gym_id": str(DISTRICT_11_GYM_ID)}
    path = "/api/v1/admin/gym-locations/workforce/assignments"
    for key in ("m1", "s1", "p11"):
        assert (await client.put(path, headers=auth(world[key]), json=body)).status_code == 403
    moved = await client.put(path, headers=auth(world["owner"]), json=body)
    assert moved.status_code == 200, moved.text
    async with sessions() as session:
        rows = (await session.execute(select(WorkforceGymAssignment).where(WorkforceGymAssignment.user_id == world["s1"].id))).scalars().all()
        assert sorted((row.gym_id == DISTRICT_11_GYM_ID, row.is_active) for row in rows) == [(False, False), (True, True)]
        audit = (await session.execute(select(AuditLog).where(AuditLog.action == "workforce_gym_assignment.updated", AuditLog.target_user_id == world["s1"].id))).scalars().all()
        assert len(audit) == 1 and audit[0].actor_user_id == world["owner"].id
