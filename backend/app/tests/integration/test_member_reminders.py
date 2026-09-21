from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.attendance import AttendanceSession
from app.models.classes import ClassBooking, GymClass
from app.models.operations import Notification, NotificationPreference
from app.services.notification_service import NotificationService

pytestmark = pytest.mark.asyncio


async def test_class_reminders_are_preference_aware_actionable_and_deduplicated(client, storage, eligible_members):
    sessions, _ = storage
    users, headers = eligible_members
    now = datetime(2026, 9, 21, 2, 0, tzinfo=UTC)
    async with sessions() as session:
        gym_class = GymClass(
            title="Morning strength",
            class_type="Strength",
            capacity=12,
            start_at=now + timedelta(minutes=90),
            end_at=now + timedelta(minutes=150),
            location="Studio A",
        )
        session.add(gym_class)
        await session.flush()
        bookings = [ClassBooking(class_id=gym_class.id, user_id=user.id, status="booked") for user in users]
        session.add_all([
            *bookings,
            NotificationPreference(user_id=users[1].id, class_reminders_enabled=False),
            NotificationPreference(user_id=users[2].id, in_app_enabled=False),
        ])
        await session.commit()

    async with sessions() as session:
        service = NotificationService(session)
        assert await service.send_class_reminders(now=now, lead_minutes=120) == 1
        assert await service.send_class_reminders(now=now, lead_minutes=180) == 0
        notifications = (await session.execute(select(Notification))).scalars().all()
        assert len(notifications) == 1
        assert notifications[0].user_id == users[0].id
        assert notifications[0].action_type == "class_booking"
        assert notifications[0].action_id == bookings[0].id
        assert "Asia/Ho_Chi_Minh" in notifications[0].message

    inbox = await client.get("/api/v1/notifications/me?page=1&page_size=20", headers=headers[0])
    assert inbox.status_code == 200
    assert inbox.json()["items"][0]["action_id"] == str(bookings[0].id)
    assert (await client.get("/api/v1/notifications/me?page=1&page_size=20", headers=headers[1])).json()["items"] == []


async def test_attendance_visit_days_use_the_configured_gym_timezone(client, storage, eligible_members):
    sessions, _ = storage
    users, headers = eligible_members
    async with sessions() as session:
        session.add_all([
            AttendanceSession(user_id=users[0].id, checked_in_at=datetime(2026, 9, 20, 16, 30, tzinfo=UTC), status="checked_out", source="iot_scanner"),
            AttendanceSession(user_id=users[0].id, checked_in_at=datetime(2026, 9, 20, 17, 30, tzinfo=UTC), status="checked_out", source="iot_scanner"),
            AttendanceSession(user_id=users[0].id, checked_in_at=datetime(2026, 9, 21, 2, 0, tzinfo=UTC), status="checked_out", source="iot_scanner"),
        ])
        await session.commit()

    response = await client.get("/api/v1/attendance/me?page=1&page_size=20", headers=headers[0])
    assert response.status_code == 200
    assert response.json()["gym_timezone"] == "Asia/Ho_Chi_Minh"
    assert response.json()["distinct_visit_days"] == ["2026-09-21", "2026-09-20"]
