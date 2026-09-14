from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.models.billing import Payment
from app.models.attendance import AttendanceSession, AttendanceEvent
from app.models.classes import ClassBooking, GymClass
from app.models.membership import MembershipPlan, UserMembership
from app.models.user import User
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.attendance_repository import AttendanceRepository

pytestmark = pytest.mark.asyncio


async def test_popularity_counts_unique_members_once_and_capacity_without_join_multiplication(storage):
    sessions, _ = storage
    start = datetime(2026, 9, 1, tzinfo=UTC)
    async with sessions() as session:
        users = [User(id=uuid4(), name=f"Member {i}", email=f"member{i}@example.com", phone=f"1234567{i}", password_hash="unused") for i in range(2)]
        classes = [GymClass(id=uuid4(), title=f"Strength {i}", class_type="Strength", capacity=10, start_at=start + timedelta(days=i), end_at=start + timedelta(days=i, hours=1), location="Studio", status="cancelled" if i == 2 else "completed") for i in range(3)]
        session.add_all([*users, *classes])
        await session.flush()
        session.add_all([
            ClassBooking(class_id=classes[0].id, user_id=users[0].id, status="booked"),
            ClassBooking(class_id=classes[0].id, user_id=users[1].id, status="cancelled"),
            ClassBooking(class_id=classes[1].id, user_id=users[0].id, status="booked"),
            ClassBooking(class_id=classes[1].id, user_id=users[1].id, status="booked"),
            ClassBooking(class_id=classes[2].id, user_id=users[1].id, status="booked"),
        ])
        await session.commit()
        rows = await AnalyticsRepository(session).class_popularity(date_from=start, date_to=start + timedelta(days=30))
        assert [tuple(row) for row in rows] == [("Strength", 2, 3, 2, 20)]
        assert await AnalyticsRepository(session).class_popularity(date_from=start - timedelta(days=30), date_to=start - timedelta(days=1)) == []


async def test_membership_months_use_utc_and_revenue_excludes_failed_payments(storage):
    sessions, _ = storage
    boundary = datetime(2026, 9, 1, tzinfo=UTC)
    async with sessions() as session:
        user = User(id=uuid4(), name="Member", email="member@example.com", phone="123456789", password_hash="unused")
        plan = MembershipPlan(id=uuid4(), name="Monthly", duration_months=1, duration_days=30, base_price=Decimal("720000"))
        session.add_all([user, plan])
        await session.flush()
        session.add(UserMembership(user_id=user.id, plan_id=plan.id, status="active", start_date=date(2026, 9, 1), expiry_date=date(2026, 10, 1), created_at=boundary))
        for index, (status, created) in enumerate([("succeeded", boundary), ("failed", boundary), ("succeeded", boundary - timedelta(seconds=1))]):
            session.add(Payment(user_id=user.id, plan_id=plan.id, amount=Decimal("720000"), discount_amount=0, status=status, idempotency_key=f"test-{index}", mock_reference=f"test-{index}", created_at=created))
        await session.commit()
        await session.execute(text("SET TIME ZONE 'America/Los_Angeles'"))
        repo = AnalyticsRepository(session)
        rows = await repo.membership_trends(date_from=boundary, date_to=boundary + timedelta(days=1))
        assert rows[0][0] == date(2026, 9, 1)
        assert rows[0][1] == rows[0][8] == 1
        revenue = await repo.revenue_summary(date_from=boundary, date_to=boundary + timedelta(days=1))
        assert tuple(revenue) == (1, Decimal("720000"), Decimal("0"))


async def test_heatmap_and_closed_visit_duration_use_utc(storage, eligible_members):
    sessions, _ = storage
    users, _ = eligible_members
    start = datetime(2026, 9, 1, 0, 30, tzinfo=UTC)
    async with sessions() as session:
        visit = AttendanceSession(user_id=users[0].id, checked_in_at=start, closed_at=start + timedelta(minutes=45), status="checked_out")
        session.add(visit)
        await session.flush()
        session.add(AttendanceEvent(session_id=visit.id, user_id=users[0].id, event_type="check_in", event_at=start, source="iot_scanner"))
        await session.commit()
        await session.execute(text("SET TIME ZONE 'America/Los_Angeles'"))
        bounds = {"date_from": start - timedelta(hours=1), "date_to": start + timedelta(hours=1)}
        assert await AttendanceRepository(session).peak_hours(**bounds) == [(2, 0, 1)]
        attendance = await AnalyticsRepository(session).attendance_summary(**bounds)
        assert tuple(attendance) == (1, 1, Decimal("45"))
