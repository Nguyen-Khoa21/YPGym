import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.classes import ClassBooking, ClassWaitlist, GymClass
from app.models.membership import UserMembership
from app.models.operations import Notification

pytestmark = pytest.mark.asyncio


async def test_last_place_race_waitlist_skip_and_repeat_cancellation(client, storage, eligible_members):
    sessions, _ = storage
    users, headers = eligible_members
    start = datetime.now(UTC) + timedelta(days=3)
    async with sessions() as session:
        gym_class = GymClass(title="Last place", class_type="Strength", capacity=1, start_at=start, end_at=start + timedelta(hours=1), location="Studio")
        session.add(gym_class)
        await session.commit()
    path = f"/api/v1/classes/{gym_class.id}"
    results = await asyncio.gather(*[client.post(f"{path}/book", headers=header) for header in headers[:2]])
    assert sorted(response.status_code for response in results) == [200, 409]
    winner = next(i for i, response in enumerate(results) if response.status_code == 200)
    loser = 1 - winner
    booking_id = results[winner].json()["id"]
    assert (await client.post(f"{path}/book", headers=headers[winner])).status_code == 409
    first = await client.post(f"{path}/waitlist", headers=headers[loser])
    second = await client.post(f"{path}/waitlist", headers=headers[2])
    assert first.status_code == second.status_code == 200
    assert (first.json()["position"], second.json()["position"]) == (1, 2)
    assert (await client.post(f"{path}/waitlist", headers=headers[loser])).status_code == 409
    assert (await client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers[loser])).status_code == 404
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == users[loser].id))).scalar_one()
        membership.status = "revoked"
        await session.commit()
    cancelled = await asyncio.gather(*[client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers[winner]) for _ in range(2)])
    assert all(response.status_code == 200 for response in cancelled)
    async with sessions() as session:
        booked = (await session.execute(select(ClassBooking).where(ClassBooking.status == "booked"))).scalars().all()
        assert len(booked) == 1 and booked[0].user_id == users[2].id
        assert (await session.get(ClassWaitlist, UUID(first.json()["id"]))).status == "cancelled"
        assert (await session.get(ClassWaitlist, UUID(second.json()["id"]))).status == "promoted"
        notifications = (await session.execute(select(Notification).where(Notification.user_id == users[2].id))).scalars().all()
        assert {item.channel for item in notifications} == {"email", "in_app"}
        assert len(notifications) == 2
