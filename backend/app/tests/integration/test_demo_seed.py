from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.db import seed
from app.models.attendance import AttendanceEvent, AttendanceSession
from app.models.billing import Invoice, Payment
from app.models.classes import ClassBooking, ClassWaitlist, GymClass, PersonalTrainer
from app.models.membership import MembershipPlan, UserMembership
from app.models.operations import BroadcastAnnouncement, Notification, NotificationPreference
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def test_demo_seed_repeatability_relative_dates_and_invoice_snapshot(storage, monkeypatch):
    sessions, _ = storage
    monkeypatch.setattr(seed, "AsyncSessionLocal", sessions)
    now = datetime.now(UTC)
    await seed.seed_development_data(demo=True, now=now)
    await seed.seed_development_data(demo=True, now=now)
    expected_counts = {
        User: 12, UserMembership: 7, MembershipPlan: 6, PersonalTrainer: 1,
        GymClass: 3, ClassBooking: 2, ClassWaitlist: 1, Payment: 1, Invoice: 1,
        Notification: 8, NotificationPreference: 12, AttendanceSession: 22, AttendanceEvent: 44,
        BroadcastAnnouncement: 1,
    }
    async with sessions() as session:
        for model, expected in expected_counts.items():
            assert (await session.scalar(select(func.count()).select_from(model))) == expected, model.__tablename__
        users = (await session.scalars(select(User))).all()
        assert {user.role for user in users} == {"admin", "manager", "staff", "pt", "member"}
        assert {user.tier for user in users if user.role == "member"} == {"normal", "advance", "vip"}
        assert set(await session.scalars(select(UserMembership.status))) == {"active", "frozen", "expired", "revoked", "cancelled"}
        invoice = (await session.scalars(select(Invoice))).one()
        invoice_snapshot = (invoice.id, invoice.amount, invoice.transaction_date, invoice.membership_start_date, invoice.membership_expiry_date)
        assert invoice.amount == Decimal("5508000.00")
        original_classes = set(await session.scalars(select(GymClass.id)))
    later = now + timedelta(days=400)
    await seed.seed_development_data(demo=True, now=later)
    async with sessions() as session:
        for model, expected in expected_counts.items():
            assert (await session.scalar(select(func.count()).select_from(model))) == expected
        assert set(await session.scalars(select(GymClass.id))) == original_classes
        assert all(start > later for start in await session.scalars(select(GymClass.start_at)))
        assert (await session.scalar(select(UserMembership.expiry_date).where(UserMembership.status == "expired"))) == later.date() - timedelta(days=1)
        assert all(expiry > later.date() for expiry in await session.scalars(select(UserMembership.expiry_date).where(UserMembership.status == "active")))
        invoice = (await session.scalars(select(Invoice))).one()
        assert (invoice.id, invoice.amount, invoice.transaction_date, invoice.membership_start_date, invoice.membership_expiry_date) == invoice_snapshot
        visits = (await session.scalars(select(AttendanceSession).where(AttendanceSession.source == "release_demo"))).all()
        assert all(later - timedelta(days=8) < visit.checked_in_at < later for visit in visits)


async def test_demo_accounts_have_live_access_states_booking_and_promotion(client, storage, monkeypatch):
    sessions, _ = storage
    monkeypatch.setattr(seed, "AsyncSessionLocal", sessions)
    await seed.seed_development_data(demo=True)
    headers = {}
    for slug in ["member", *[row[0] for row in seed.DEMO_MEMBERS]]:
        login = await client.post("/api/v1/auth/login", json={"email": f"{slug}@ypgym.dev", "password": seed.get_settings().DEVELOPMENT_SEED_PASSWORD})
        assert login.status_code == 200, slug
        headers[slug] = {"Authorization": f"Bearer {login.json()['access_token']}"}
        dashboard = await client.get("/api/v1/dashboard/me", headers=headers[slug])
        assert dashboard.status_code == 200
        eligible = slug in {"member", "advance", "normal"}
        assert dashboard.json()["qr_access"]["eligible"] is eligible
        assert (await client.get("/api/v1/attendance/qr-token/me", headers=headers[slug])).status_code == (200 if eligible else 403)
    async with sessions() as session:
        full_class = (await session.scalars(select(GymClass).where(GymClass.title == "Capacity One Demo"))).one()
        booking = (await session.scalars(select(ClassBooking).where(ClassBooking.class_id == full_class.id))).one()
        normal_id = (await session.scalar(select(User.id).where(User.email == "normal@ypgym.dev")))
    path = f"/api/v1/classes/{full_class.id}"
    assert (await client.post(f"{path}/book", headers=headers["member"])).status_code == 409
    waitlist = await client.post(f"{path}/waitlist", headers=headers["member"])
    assert waitlist.status_code == 200 and waitlist.json()["position"] == 2
    assert (await client.post(f"/api/v1/bookings/{booking.id}/cancel", headers=headers["advance"])).status_code == 200
    # Re-seeding retains the completed cancellation/promotion and cannot overbook.
    await seed.seed_development_data(demo=True)
    async with sessions() as session:
        booked = (await session.scalars(select(ClassBooking).where(ClassBooking.class_id == full_class.id, ClassBooking.status == "booked"))).all()
        assert len(booked) == 1 and booked[0].user_id == normal_id
        promoted = (await session.scalars(select(ClassWaitlist).where(ClassWaitlist.user_id == normal_id))).one()
        assert promoted.status == "promoted"
        notifications = (await session.scalars(select(Notification).where(Notification.user_id == normal_id, Notification.notification_type == "waitlist_promoted"))).all()
        assert {item.channel for item in notifications} == {"in_app", "email"}
    plans = (await client.get("/api/v1/membership-plans")).json()
    monthly = next(plan for plan in plans if plan["duration_months"] == 1)
    purchase = await client.post("/api/v1/memberships/purchase", headers=headers["member"],
                                 json={"plan_id": monthly["id"], "idempotency_key": "seed-preserves-renewal", "mock_payment_confirmed": True})
    assert purchase.status_code == 200
    paid_expiry = purchase.json()["membership"]["expiry_date"]
    invoice = purchase.json()["invoice"]
    await seed.seed_development_data(demo=True)
    dashboard = (await client.get("/api/v1/dashboard/me", headers=headers["member"])).json()
    assert dashboard["membership"]["expiry_date"] == paid_expiry
    async with sessions() as session:
        saved = await session.get(Invoice, UUID(invoice["id"]))
        assert saved.membership_expiry_date.isoformat() == paid_expiry


async def test_full_demo_seed_refuses_normal_and_production_storage(monkeypatch):
    from app.core.config import Settings

    settings = Settings(_env_file=None, ENVIRONMENT="development",
                        DATABASE_URL="postgresql+asyncpg://local:unused@localhost:5433/ypgym",
                        REDIS_URL="redis://localhost:6380/0")
    monkeypatch.setattr(seed, "get_settings", lambda: settings)
    with pytest.raises(ValueError, match="isolated storage"):
        await seed.seed_development_data(demo=True)
    settings.DATABASE_URL = "postgresql+asyncpg://demo:unused@postgres-db:5432/ypgym_demo"
    settings.REDIS_URL = "redis://redis-cache:6379/0"
    settings.ENVIRONMENT = "production"
    with pytest.raises(ValueError, match="production"):
        await seed.seed_development_data(demo=True)
