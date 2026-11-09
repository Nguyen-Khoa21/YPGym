from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.gym import DISTRICT_1_GYM_ID, DISTRICT_11_GYM_ID, WorkforceGymAssignment
from app.models.membership import MembershipPlan, UserMembership
from app.models.user import User
from app.utils.security import create_access_token


pytestmark = pytest.mark.asyncio


def auth(user: User) -> dict[str, str]:
    token = create_access_token(user_id=user.id, role=user.role, tier=user.tier)[0]
    return {"Authorization": f"Bearer {token}"}


async def create_users(storage):
    sessions, _ = storage
    today = date.today()
    async with sessions() as session:
        plan = MembershipPlan(
            name=f"Multi-gym plan {uuid4().hex[:8]}",
            duration_months=1,
            duration_days=30,
            base_price=Decimal("720000"),
        )
        admin = User(
            name="Multi-gym Admin",
            email=f"admin-{uuid4().hex[:8]}@example.com",
            phone=f"09{uuid4().int % 100000000:08d}",
            password_hash="unused",
            is_email_verified=True,
            role="admin",
        )
        manager = User(
            name="District 11 Manager",
            email=f"manager-{uuid4().hex[:8]}@example.com",
            phone=f"08{uuid4().int % 100000000:08d}",
            password_hash="unused",
            is_email_verified=True,
            role="manager",
        )
        district_1_member = User(
            name="District 1 Member",
            email=f"member-d1-{uuid4().hex[:8]}@example.com",
            phone=f"07{uuid4().int % 100000000:08d}",
            password_hash="unused",
            is_email_verified=True,
        )
        district_11_member = User(
            name="District 11 Member",
            email=f"member-d11-{uuid4().hex[:8]}@example.com",
            phone=f"06{uuid4().int % 100000000:08d}",
            password_hash="unused",
            is_email_verified=True,
        )
        session.add_all([plan, admin, manager, district_1_member, district_11_member])
        await session.flush()
        session.add_all(
            [
                WorkforceGymAssignment(
                    user_id=manager.id,
                    gym_id=DISTRICT_11_GYM_ID,
                    assigned_role="manager",
                ),
                UserMembership(
                    user_id=district_1_member.id,
                    home_gym_id=DISTRICT_1_GYM_ID,
                    plan_id=plan.id,
                    status="active",
                    start_date=today,
                    expiry_date=today + timedelta(days=30),
                ),
                UserMembership(
                    user_id=district_11_member.id,
                    home_gym_id=DISTRICT_11_GYM_ID,
                    plan_id=plan.id,
                    status="active",
                    start_date=today,
                    expiry_date=today + timedelta(days=30),
                ),
            ]
        )
        await session.commit()
    return admin, manager, district_1_member, district_11_member


async def test_classes_are_listed_and_overlap_checked_per_gym(client, storage):
    admin, manager, district_1_member, district_11_member = await create_users(storage)
    start = datetime.now(UTC) + timedelta(days=3)

    def payload(gym_id, title):
        return {
            "gym_id": str(gym_id),
            "title": title,
            "class_type": "Strength",
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(hours=1)).isoformat(),
            "capacity": 12,
            "price_vnd": 150000,
            "location": "Studio A",
        }

    district_1_class = await client.post(
        "/api/v1/admin/classes",
        headers=auth(admin),
        json=payload(DISTRICT_1_GYM_ID, "District 1 strength"),
    )
    district_11_class = await client.post(
        "/api/v1/admin/classes",
        headers=auth(admin),
        json=payload(DISTRICT_11_GYM_ID, "District 11 strength"),
    )
    assert district_1_class.status_code == district_11_class.status_code == 200
    conflict = await client.post(
        "/api/v1/admin/classes",
        headers=auth(admin),
        json=payload(DISTRICT_1_GYM_ID, "District 1 overlap"),
    )
    assert conflict.status_code == 409
    assert (await client.post(
        "/api/v1/admin/classes",
        headers=auth(manager),
        json=payload(DISTRICT_11_GYM_ID, "Manager class"),
    )).status_code == 403

    default_listing = await client.get("/api/v1/classes/upcoming", headers=auth(district_11_member))
    assert default_listing.status_code == 200
    assert default_listing.json()["gym_id"] == str(DISTRICT_11_GYM_ID)
    assert [item["id"] for item in default_listing.json()["items"]] == [district_11_class.json()["id"]]

    switched_listing = await client.get(
        "/api/v1/classes/upcoming",
        headers=auth(district_11_member),
        params={"gym_id": str(DISTRICT_1_GYM_ID)},
    )
    assert switched_listing.status_code == 200
    assert [item["id"] for item in switched_listing.json()["items"]] == [district_1_class.json()["id"]]
    district_1_default = await client.get("/api/v1/classes/upcoming", headers=auth(district_1_member))
    assert [item["id"] for item in district_1_default.json()["items"]] == [district_1_class.json()["id"]]


async def test_broadcasts_combine_chain_and_home_gym_scope(client, storage):
    admin, manager, district_1_member, district_11_member = await create_users(storage)
    starts_at = datetime.now(UTC) - timedelta(minutes=1)
    base = {
        "audience": "all",
        "message": "A location-aware member announcement.",
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(days=1)).isoformat(),
    }
    chain = await client.post(
        "/api/v1/admin/broadcasts",
        headers=auth(admin),
        json={**base, "title": "Chain notice", "gym_id": None},
    )
    district_1 = await client.post(
        "/api/v1/admin/broadcasts",
        headers=auth(admin),
        json={**base, "title": "District 1 notice", "gym_id": str(DISTRICT_1_GYM_ID)},
    )
    district_11 = await client.post(
        "/api/v1/admin/broadcasts",
        headers=auth(manager),
        json={**base, "title": "District 11 notice"},
    )
    assert chain.status_code == district_1.status_code == district_11.status_code == 200
    assert chain.json()["gym_id"] is None
    assert district_11.json()["gym_id"] == str(DISTRICT_11_GYM_ID)

    cross_gym = await client.post(
        "/api/v1/admin/broadcasts",
        headers=auth(manager),
        json={**base, "title": "Wrong branch", "gym_id": str(DISTRICT_1_GYM_ID)},
    )
    assert cross_gym.status_code == 403

    district_1_titles = {
        item["title"]
        for item in (await client.get("/api/v1/notifications/broadcasts/active", headers=auth(district_1_member))).json()
    }
    district_11_titles = {
        item["title"]
        for item in (await client.get("/api/v1/notifications/broadcasts/active", headers=auth(district_11_member))).json()
    }
    assert district_1_titles == {"Chain notice", "District 1 notice"}
    assert district_11_titles == {"Chain notice", "District 11 notice"}

    manager_history = (await client.get("/api/v1/admin/broadcasts", headers=auth(manager))).json()
    assert [item["title"] for item in manager_history] == ["District 11 notice"]
