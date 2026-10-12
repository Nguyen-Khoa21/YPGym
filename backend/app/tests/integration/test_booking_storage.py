from datetime import UTC, datetime, timedelta

import pytest

from app.models.classes import ClassBooking, GymClass

pytestmark = pytest.mark.asyncio


async def test_historical_booking_remains_confirmed_without_fabricated_payment(client, storage, eligible_members):
    sessions, _ = storage
    users, headers = eligible_members
    start = datetime.now(UTC) + timedelta(days=3)
    async with sessions() as session:
        gym_class = GymClass(
            title="Legacy reservation",
            class_type="Strength",
            capacity=1,
            price_vnd=150_000,
            start_at=start,
            end_at=start + timedelta(hours=1),
            location="Studio",
        )
        session.add(gym_class)
        await session.flush()
        booking = ClassBooking(
            class_id=gym_class.id,
            user_id=users[0].id,
            status="confirmed",
            entitlement_source="legacy",
            price_vnd=None,
            confirmed_at=datetime.now(UTC),
        )
        session.add(booking)
        await session.commit()

    response = await client.get("/api/v1/bookings/me", headers=headers[0])
    assert response.status_code == 200
    item = next(row for row in response.json()["bookings"] if row["id"] == str(booking.id))
    assert item["status"] == "confirmed"
    assert item["entitlement_source"] == "legacy"
    assert item["price_vnd"] is None
    assert item["payment_id"] is None
