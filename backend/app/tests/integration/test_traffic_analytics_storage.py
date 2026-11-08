from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models.attendance import AttendanceSession
from app.models.gym import DISTRICT_1_GYM_ID, DISTRICT_11_GYM_ID, WorkforceGymAssignment
from app.models.membership import UserMembership
from app.models.user import User
from app.services.traffic_analytics_service import previous_completed_month
from app.utils.security import create_access_token


pytestmark = pytest.mark.asyncio


async def test_previous_month_traffic_is_gym_scoped_cached_and_role_safe(
    client,
    storage,
    eligible_members,
):
    sessions, _ = storage
    users, member_headers = eligible_members
    now = datetime.now(UTC)
    timezone = ZoneInfo("Asia/Ho_Chi_Minh")
    period_start, period_end = previous_completed_month(now, timezone)
    manager = User(
        id=uuid4(),
        name="District 1 Analytics Manager",
        email="traffic-manager-dist1@example.com",
        password_hash="unused",
        role="manager",
        is_email_verified=True,
    )
    staff = User(
        id=uuid4(),
        name="District 1 Analytics Staff",
        email="traffic-staff-dist1@example.com",
        password_hash="unused",
        role="staff",
        is_email_verified=True,
    )
    owner = User(
        id=uuid4(),
        name="Traffic Owner",
        email="traffic-owner@example.com",
        password_hash="unused",
        role="admin",
        is_email_verified=True,
    )
    async with sessions() as session:
        district_11_membership = (
            await session.execute(
                select(UserMembership).where(UserMembership.user_id == users[1].id),
            )
        ).scalar_one()
        district_11_membership.home_gym_id = DISTRICT_11_GYM_ID
        session.add_all([manager, staff, owner])
        await session.flush()
        session.add_all(
            [
                WorkforceGymAssignment(
                    user_id=manager.id,
                    gym_id=DISTRICT_1_GYM_ID,
                    assigned_role="manager",
                ),
                WorkforceGymAssignment(
                    user_id=staff.id,
                    gym_id=DISTRICT_1_GYM_ID,
                    assigned_role="staff",
                ),
            ],
        )
        for day_offset in range(4):
            district_1_start = (period_start + timedelta(days=day_offset, hours=18)).astimezone(UTC)
            district_11_start = (period_start + timedelta(days=day_offset, hours=8)).astimezone(UTC)
            session.add_all(
                [
                    AttendanceSession(
                        gym_id=DISTRICT_1_GYM_ID,
                        user_id=users[0].id,
                        checked_in_at=district_1_start,
                        closed_at=district_1_start + timedelta(hours=1),
                        status="checked_out",
                        source="multigym_demo",
                    ),
                    AttendanceSession(
                        gym_id=DISTRICT_11_GYM_ID,
                        user_id=users[1].id,
                        checked_in_at=district_11_start,
                        closed_at=district_11_start + timedelta(hours=1),
                        status="checked_out",
                        source="iot_scanner",
                    ),
                ],
            )
        boundary_start = period_start.astimezone(UTC) - timedelta(minutes=30)
        session.add(
            AttendanceSession(
                gym_id=DISTRICT_1_GYM_ID,
                user_id=users[0].id,
                checked_in_at=boundary_start,
                closed_at=boundary_start + timedelta(hours=1),
                status="checked_out",
                source="iot_scanner",
            ),
        )
        outside = period_end.astimezone(UTC) + timedelta(hours=1)
        session.add(
            AttendanceSession(
                gym_id=DISTRICT_1_GYM_ID,
                user_id=users[0].id,
                checked_in_at=outside,
                closed_at=outside + timedelta(hours=1),
                status="checked_out",
                source="iot_scanner",
            ),
        )
        await session.commit()

    district_1_response = await client.get("/api/v1/attendance/traffic-summary", headers=member_headers[0])
    district_11_response = await client.get("/api/v1/attendance/traffic-summary", headers=member_headers[1])
    assert district_1_response.status_code == district_11_response.status_code == 200
    district_1 = district_1_response.json()
    district_11 = district_11_response.json()
    assert district_1["gym_id"] == str(DISTRICT_1_GYM_ID)
    assert district_11["gym_id"] == str(DISTRICT_11_GYM_ID)
    assert district_1["busiest_window"]["label"] == "6:00 PM–8:00 PM"
    assert district_11["busiest_window"]["label"] == "8:00 AM–10:00 AM"
    assert district_1["overlapping_sessions"] == 5
    assert district_1["visits"] == 4
    assert district_1["contains_demo_data"] is True
    assert district_11["contains_demo_data"] is False
    assert district_1["methodology"]["sample_interval_minutes"] == 15
    assert district_1["methodology"]["bucket_minutes"] == 120
    assert len(district_1["buckets"]) == 12
    assert len(district_1["weekday_buckets"]) == 84

    cached = (await client.get("/api/v1/attendance/traffic-summary", headers=member_headers[0])).json()
    assert cached["cache_hit"] is True
    staff_token, _ = create_access_token(user_id=staff.id, role="staff", tier="normal")
    staff_response = await client.get(
        "/api/v1/admin/analytics/traffic-summary",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert staff_response.status_code == 403

    manager_token, _ = create_access_token(user_id=manager.id, role="manager", tier="normal")
    manager_headers = {"Authorization": f"Bearer {manager_token}"}
    manager_summary = await client.get("/api/v1/admin/analytics/traffic-summary", headers=manager_headers)
    assert manager_summary.status_code == 200
    assert manager_summary.json()["gym_id"] == str(DISTRICT_1_GYM_ID)
    forbidden_manager = await client.get(
        f"/api/v1/admin/analytics/traffic-summary?gym_id={DISTRICT_11_GYM_ID}",
        headers=manager_headers,
    )
    assert forbidden_manager.status_code == 403

    owner_token, _ = create_access_token(user_id=owner.id, role="admin", tier="normal")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    owner_default = await client.get("/api/v1/admin/analytics/traffic-summary", headers=owner_headers)
    owner_district_11 = await client.get(
        f"/api/v1/admin/analytics/traffic-summary?gym_id={DISTRICT_11_GYM_ID}",
        headers=owner_headers,
    )
    assert owner_default.json()["gym_id"] == str(DISTRICT_1_GYM_ID)
    assert owner_district_11.status_code == 200
    assert owner_district_11.json()["gym_id"] == str(DISTRICT_11_GYM_ID)
