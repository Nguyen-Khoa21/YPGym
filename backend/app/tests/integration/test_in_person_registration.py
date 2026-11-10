"""Staff in-person registration, QR checkout, cash payment and payment-status scope."""
import json
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.billing import Invoice, Payment
from app.models.gym import DISTRICT_1_GYM_ID, DISTRICT_11_GYM_ID, WorkforceGymAssignment
from app.models.membership import MembershipPlan, UserMembership
from app.models.operations import AuditLog
from app.models.user import User
from app.services.payos_service import PayOSClient
from app.tests.integration.test_payos_payment import webhook
from app.utils.security import create_access_token

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def mock_payos_link_creation(monkeypatch):
    async def create_payment_link(self, *, order_code, amount, description, expired_at):
        return SimpleNamespace(
            order_code=order_code,
            amount=amount,
            payment_link_id=f"link-{order_code}",
            checkout_url=f"https://pay.payos.vn/web/link-{order_code}",
            qr_code=f"00020101-qr-{order_code}",
        )

    monkeypatch.setattr(PayOSClient, "create_payment_link", create_payment_link)


async def workforce(storage, role: str, gym_id=None, *, on_shift: bool = False, client=None):
    sessions, _ = storage
    user = User(name=f"{role} test", email=f"{role}-{uuid4().hex[:8]}@example.com", password_hash="unused", role=role, is_email_verified=True)
    async with sessions() as session:
        session.add(user)
        await session.flush()
        if gym_id is not None:
            session.add(WorkforceGymAssignment(user_id=user.id, gym_id=gym_id, assigned_role=role))
        await session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(user_id=user.id, role=role, tier='normal')[0]}"}
    if on_shift:
        assert (await client.post("/api/v1/staff/shifts/clock-in", headers=headers)).status_code == 201
    return user, headers


async def make_plan(storage) -> MembershipPlan:
    sessions, _ = storage
    async with sessions() as session:
        plan = MembershipPlan(name=f"Walk-in plan {uuid4().hex[:6]}", duration_months=1, duration_days=30, base_price=Decimal("720000"))
        session.add(plan)
        await session.commit()
        return plan


def body(**overrides):
    base = {"name": "Walk In", "email": f"walkin-{uuid4().hex[:8]}@example.com", "phone": f"09{uuid4().int % 100000000:08d}"}
    return {**base, **overrides}


async def register(client, headers, **overrides):
    return await client.post("/api/v1/staff/members", headers=headers, json=body(**overrides))


async def test_registration_needs_open_shift_then_creates_verified_member_without_leaking_password(client, storage):
    sessions, _ = storage
    staff, headers = await workforce(storage, "staff", DISTRICT_1_GYM_ID)
    locked = await register(client, headers)
    assert locked.status_code == 403 and locked.json()["error"]["code"] == "SHIFT_REQUIRED"

    assert (await client.post("/api/v1/staff/shifts/clock-in", headers=headers)).status_code == 201
    created = await register(client, headers)
    assert created.status_code == 201, created.text
    assert created.headers["cache-control"] == "no-store"
    data = created.json()
    password = data["temporary_password"]
    assert len(password) >= 16 and data["member"]["gym_id"] == str(DISTRICT_1_GYM_ID)

    async with sessions() as session:
        member = await session.get(User, data["member"]["id"])
        assert member.role == "member" and member.is_email_verified and member.email_verified_at is not None
        assert member.must_change_password and member.registration_channel == "in_person"
        assert member.registered_by_user_id == staff.id
        assert member.password_hash != password
        audits = (await session.execute(select(AuditLog).where(AuditLog.action == "member.registered_in_person"))).scalars().all()
        assert len(audits) == 1
        assert password not in json.dumps([[a.summary, a.reason, a.outcome, a.before_data, a.after_data] for a in audits], default=str)

    login = await client.post("/api/v1/auth/login", json={"email": data["member"]["email"], "password": password})
    assert login.status_code == 200, login.text
    assert login.json()["user"]["must_change_password"] is True
    assert password not in json.dumps((await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})).json())


async def test_duplicate_identity_returns_the_online_error_codes(client, storage):
    _, headers = await workforce(storage, "staff", DISTRICT_1_GYM_ID, on_shift=True, client=client)
    first = (await register(client, headers)).json()["member"]
    dup_email = await register(client, headers, email=first["email"])
    dup_phone = await register(client, headers, phone=first["phone"])
    assert (dup_email.status_code, dup_email.json()["error"]["code"]) == (409, "EMAIL_ALREADY_EXISTS")
    assert (dup_phone.status_code, dup_phone.json()["error"]["code"]) == (409, "PHONE_ALREADY_EXISTS")


async def test_gym_is_derived_on_the_server(client, storage):
    _, staff = await workforce(storage, "staff", DISTRICT_1_GYM_ID, on_shift=True, client=client)
    other_gym = await register(client, staff, gym_id=str(DISTRICT_11_GYM_ID))
    assert other_gym.status_code == 403
    _, owner = await workforce(storage, "admin")
    assert (await register(client, owner)).status_code == 422
    owned = await register(client, owner, gym_id=str(DISTRICT_11_GYM_ID))
    assert owned.status_code == 201 and owned.json()["member"]["gym_id"] == str(DISTRICT_11_GYM_ID)


async def test_member_role_cannot_use_staff_registration(client, storage):
    sessions, _ = storage
    member = User(name="Member", email=f"m-{uuid4().hex[:8]}@example.com", password_hash="unused", is_email_verified=True)
    async with sessions() as session:
        session.add(member)
        await session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(user_id=member.id, role='member', tier='normal')[0]}"}
    assert (await register(client, headers)).status_code == 403


async def test_qr_checkout_settles_only_after_verified_webhook_and_status_is_gym_scoped(client, storage):
    sessions, _ = storage
    plan = await make_plan(storage)
    _, d1 = await workforce(storage, "staff", DISTRICT_1_GYM_ID, on_shift=True, client=client)
    _, d11 = await workforce(storage, "staff", DISTRICT_11_GYM_ID, on_shift=True, client=client)
    member = (await register(client, d1)).json()["member"]

    key = f"qr-{uuid4().hex}"
    request = {"plan_id": str(plan.id), "idempotency_key": key}
    checkout = await client.post(f"/api/v1/staff/members/{member['id']}/membership-checkout", headers=d1, json=request)
    assert checkout.status_code == 201, checkout.text
    data = checkout.json()
    assert data["gym_id"] == str(DISTRICT_1_GYM_ID) and data["qr_code"] and data["checkout_url"].startswith("https://")
    replay = await client.post(f"/api/v1/staff/members/{member['id']}/membership-checkout", headers=d1, json=request)
    assert replay.json()["transaction_id"] == data["transaction_id"]
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Payment).where(Payment.user_id == member["id"])) == 1
        assert await session.scalar(select(func.count()).select_from(UserMembership).where(UserMembership.user_id == member["id"])) == 0

    pending = await client.get(f"/api/v1/staff/payments/{data['transaction_id']}", headers=d1)
    assert pending.status_code == 200 and pending.json()["status"] == "pending"
    assert set(pending.json()) == {"id", "status", "member_name", "plan_name", "gym_name"}
    assert (await client.get(f"/api/v1/staff/payments/{data['transaction_id']}", headers=d11)).status_code == 404

    settled = await client.post("/api/v1/payments/payos/webhook", json=webhook(data["order_code"], data["amount_vnd"]))
    assert settled.status_code == 200
    assert (await client.get(f"/api/v1/staff/payments/{data['transaction_id']}", headers=d1)).json()["status"] == "paid"
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == member["id"]))).scalar_one()
        assert membership.home_gym_id == DISTRICT_1_GYM_ID and membership.status == "active"


async def test_cash_payment_is_exactly_once_audited_and_not_client_priced(client, storage):
    sessions, _ = storage
    plan = await make_plan(storage)
    staff_user, d1 = await workforce(storage, "staff", DISTRICT_1_GYM_ID, on_shift=True, client=client)
    member = (await register(client, d1)).json()["member"]
    url = f"/api/v1/staff/members/{member['id']}/membership-cash"
    request = {"plan_id": str(plan.id), "idempotency_key": f"cash-{uuid4().hex}"}

    assert (await client.post(url, headers=d1, json={**request, "amount": 1})).status_code == 422
    first = await client.post(url, headers=d1, json=request)
    assert first.status_code == 200, first.text
    again = await client.post(url, headers=d1, json=request)
    assert again.status_code == 200
    assert again.json()["payment"]["id"] == first.json()["payment"]["id"]

    async with sessions() as session:
        payments = (await session.execute(select(Payment).where(Payment.user_id == member["id"]))).scalars().all()
        assert len(payments) == 1
        payment = payments[0]
        assert payment.provider == "cash" and payment.status == "succeeded" and payment.gym_id == DISTRICT_1_GYM_ID
        assert payment.mock_reference.startswith("CASH-") and payment.amount == Decimal("720000")
        assert await session.scalar(select(func.count()).select_from(Invoice).where(Invoice.payment_id == payment.id)) == 1
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == member["id"]))).scalar_one()
        assert membership.home_gym_id == DISTRICT_1_GYM_ID and membership.status == "active"
        audit = (await session.execute(select(AuditLog).where(AuditLog.action == "membership.cash_payment.recorded"))).scalars().all()
        assert len(audit) == 1 and audit[0].actor_user_id == staff_user.id
        assert audit[0].reason == "Cash payment received at YPGym District 1"


async def test_cash_requires_shift_and_other_gym_staff_cannot_serve_the_member(client, storage):
    plan = await make_plan(storage)
    _, d1 = await workforce(storage, "staff", DISTRICT_1_GYM_ID, on_shift=True, client=client)
    _, off_shift = await workforce(storage, "staff", DISTRICT_1_GYM_ID)
    _, d11 = await workforce(storage, "staff", DISTRICT_11_GYM_ID, on_shift=True, client=client)
    member = (await register(client, d1)).json()["member"]
    url = f"/api/v1/staff/members/{member['id']}/membership-cash"
    request = {"plan_id": str(plan.id), "idempotency_key": f"cash-{uuid4().hex}"}

    locked = await client.post(url, headers=off_shift, json=request)
    assert locked.status_code == 403 and locked.json()["error"]["code"] == "SHIFT_REQUIRED"
    assert (await client.post(url, headers=d1, json=request)).status_code == 200
    other = await client.post(url, headers=d11, json={**request, "idempotency_key": f"cash-{uuid4().hex}"})
    assert other.status_code == 403
    d11_wrong_gym = await client.post(url, headers=d11, json={**request, "gym_id": str(DISTRICT_1_GYM_ID)})
    assert d11_wrong_gym.status_code == 403


async def test_staff_cannot_charge_an_online_member_or_unknown_id(client, storage):
    sessions, _ = storage
    plan = await make_plan(storage)
    _, d1 = await workforce(storage, "staff", DISTRICT_1_GYM_ID, on_shift=True, client=client)
    online = User(name="Online", email=f"on-{uuid4().hex[:8]}@example.com", password_hash="unused", is_email_verified=True)
    async with sessions() as session:
        session.add(online)
        await session.commit()
    request = {"plan_id": str(plan.id), "idempotency_key": f"cash-{uuid4().hex}"}
    assert (await client.post(f"/api/v1/staff/members/{online.id}/membership-cash", headers=d1, json=request)).status_code == 404
    assert (await client.post(f"/api/v1/staff/members/{uuid4()}/membership-checkout", headers=d1, json=request)).status_code == 404
