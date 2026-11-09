import asyncio
import hashlib
import hmac
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.models.billing import Invoice, Payment
from app.models.classes import ClassBooking, GymClass
from app.models.email_delivery import EmailDelivery
from app.models.gym import DISTRICT_1_GYM_ID, DISTRICT_11_GYM_ID, GymLocation
from app.models.membership import MembershipPlan, UserMembership
from app.models.operations import AuditLog
from app.models.user import User
from app.services.payment_service import PayOSPaymentService
from app.services.payos_service import PayOSClient
from app.utils.security import create_access_token

pytestmark = pytest.mark.asyncio
TEST_CHECKSUM_KEY = "isolated-checksum-key"


@pytest.fixture(autouse=True)
def mock_payos_link_creation(monkeypatch):
    async def create_payment_link(self, *, order_code, amount, description, expired_at):
        return SimpleNamespace(
            order_code=order_code,
            amount=amount,
            payment_link_id=f"link-{order_code}",
            checkout_url=f"https://pay.payos.vn/web/link-{order_code}",
        )

    monkeypatch.setattr(PayOSClient, "create_payment_link", create_payment_link)


def auth(user: User, role: str = "member") -> dict[str, str]:
    token = create_access_token(user_id=user.id, role=role, tier="normal")[0]
    return {"Authorization": f"Bearer {token}"}


async def create_member_and_plan(storage, *, with_membership: bool = False):
    sessions, _ = storage
    today = date.today()
    async with sessions() as session:
        plan = MembershipPlan(
            name=f"payOS plan {uuid4().hex[:8]}",
            duration_months=1,
            duration_days=30,
            base_price=Decimal("720000"),
        )
        member = User(
            name="payOS Member",
            email=f"payos-{uuid4().hex[:8]}@example.com",
            phone=f"09{uuid4().int % 100000000:08d}",
            password_hash="unused",
            is_email_verified=True,
        )
        other = User(
            name="Other Member",
            email=f"other-{uuid4().hex[:8]}@example.com",
            phone=f"08{uuid4().int % 100000000:08d}",
            password_hash="unused",
            is_email_verified=True,
        )
        session.add_all([plan, member, other])
        await session.flush()
        if with_membership:
            session.add(UserMembership(
                user_id=member.id,
                plan_id=plan.id,
                status="active",
                start_date=today,
                expiry_date=today + timedelta(days=10),
            ))
        await session.commit()
    return plan, member, other


async def start_payment(client, plan, member, *, gym_id=DISTRICT_1_GYM_ID):
    return await client.post(
        "/api/v1/payments/payos/create",
        headers=auth(member),
        json={"membership_plan_id": str(plan.id), "gym_id": str(gym_id), "client_platform": "web"},
    )


def webhook(order_code: int, amount: int, *, reference: str | None = None, valid: bool = True) -> dict:
    data = {
        "orderCode": order_code,
        "amount": amount,
        "description": f"YPG{order_code % 1_000_000:06d}",
        "accountNumber": "masked",
        "reference": reference or f"ref-{order_code}",
        "transactionDateTime": "2026-11-03 10:30:00",
        "currency": "VND",
        "paymentLinkId": f"link-{order_code}",
        "code": "00",
        "desc": "success",
        "counterAccountBankId": None,
        "counterAccountBankName": None,
        "counterAccountName": None,
        "counterAccountNumber": None,
        "virtualAccountName": None,
        "virtualAccountNumber": None,
    }
    message = "&".join(f"{key}={'' if data[key] is None else data[key]}" for key in sorted(data))
    signature = hmac.new(TEST_CHECKSUM_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    return {"code": "00", "desc": "success", "success": True, "data": data, "signature": signature if valid else "0" * 64}


async def test_membership_checkout_uses_server_price_and_enforces_ownership(client, storage):
    plan, member, other = await create_member_and_plan(storage)
    assert (await client.post("/api/v1/payments/payos/create", json={"membership_plan_id": str(plan.id)})).status_code == 401
    tampered = await client.post(
        "/api/v1/payments/payos/create",
        headers=auth(member),
        json={"membership_plan_id": str(plan.id), "amount_vnd": 1},
    )
    assert tampered.status_code == 422

    response = await start_payment(client, plan, member)
    assert response.status_code == 201, response.text
    checkout = response.json()
    assert checkout["gym_id"] == str(DISTRICT_1_GYM_ID)
    assert checkout["gym_name"] == "YPGym District 1"
    assert checkout["amount_vnd"] == 720_000
    assert checkout["checkout_url"].startswith("https://pay.payos.vn/")
    assert isinstance(checkout["order_code"], int)
    assert (await client.get(f"/api/v1/payments/payos/{checkout['order_code']}", headers=auth(other))).status_code == 404

    sessions, _ = storage
    async with sessions() as session:
        payment = await session.get(Payment, checkout["transaction_id"])
        assert payment.gym_id == DISTRICT_1_GYM_ID
        assert (payment.provider, payment.status, payment.payos_order_code) == ("payos", "pending", checkout["order_code"])
        assert await session.scalar(select(func.count()).select_from(UserMembership)) == 0
        assert await session.scalar(select(func.count()).select_from(Invoice)) == 0


async def test_membership_gym_is_required_validated_and_applied_only_after_webhook(client, storage):
    plan, member, _ = await create_member_and_plan(storage)
    missing = await client.post(
        "/api/v1/payments/payos/create",
        headers=auth(member),
        json={"membership_plan_id": str(plan.id)},
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "GYM_SELECTION_REQUIRED"

    unknown = await start_payment(client, plan, member, gym_id=uuid4())
    assert unknown.status_code == 404

    sessions, _ = storage
    async with sessions() as session:
        district_11 = await session.get(GymLocation, DISTRICT_11_GYM_ID)
        district_11.is_active = False
        await session.commit()
    inactive = await start_payment(client, plan, member, gym_id=DISTRICT_11_GYM_ID)
    assert inactive.status_code == 404
    async with sessions() as session:
        district_11 = await session.get(GymLocation, DISTRICT_11_GYM_ID)
        district_11.is_active = True
        await session.commit()

    checkout_response = await start_payment(client, plan, member, gym_id=DISTRICT_11_GYM_ID)
    assert checkout_response.status_code == 201, checkout_response.text
    checkout = checkout_response.json()
    assert checkout["gym_id"] == str(DISTRICT_11_GYM_ID)
    async with sessions() as session:
        assert await session.scalar(
            select(func.count()).select_from(UserMembership).where(UserMembership.user_id == member.id)
        ) == 0
        payment = await session.get(Payment, checkout["transaction_id"])
        assert payment.gym_id == DISTRICT_11_GYM_ID

    settled = await client.post(
        "/api/v1/payments/payos/webhook",
        json=webhook(checkout["order_code"], checkout["amount_vnd"]),
    )
    assert settled.status_code == 200
    async with sessions() as session:
        membership = (
            await session.execute(select(UserMembership).where(UserMembership.user_id == member.id))
        ).scalar_one()
        invoice = (
            await session.execute(select(Invoice).where(Invoice.payment_id == checkout["transaction_id"]))
        ).scalar_one()
        assert membership.home_gym_id == DISTRICT_11_GYM_ID
        assert invoice.product_name == f"{plan.name} · YPGym District 11"


async def test_renewal_changes_home_gym_only_after_verified_payment(client, storage):
    plan, member, _ = await create_member_and_plan(storage, with_membership=True)
    sessions, _ = storage
    checkout_response = await start_payment(client, plan, member, gym_id=DISTRICT_11_GYM_ID)
    assert checkout_response.status_code == 201, checkout_response.text
    checkout = checkout_response.json()
    async with sessions() as session:
        membership = (
            await session.execute(select(UserMembership).where(UserMembership.user_id == member.id))
        ).scalar_one()
        assert membership.home_gym_id == DISTRICT_1_GYM_ID

    assert (await client.post(
        "/api/v1/payments/payos/webhook",
        json=webhook(checkout["order_code"], checkout["amount_vnd"]),
    )).status_code == 200
    async with sessions() as session:
        membership = (
            await session.execute(select(UserMembership).where(UserMembership.user_id == member.id))
        ).scalar_one()
        assert membership.home_gym_id == DISTRICT_11_GYM_ID


async def test_valid_webhook_is_atomic_and_duplicate_safe(client, storage):
    plan, member, _ = await create_member_and_plan(storage)
    checkout = (await start_payment(client, plan, member)).json()
    payload = webhook(checkout["order_code"], checkout["amount_vnd"])

    responses = await asyncio.gather(
        client.post("/api/v1/payments/payos/webhook", json=payload),
        client.post("/api/v1/payments/payos/webhook", json=payload),
    )
    assert [response.status_code for response in responses] == [200, 200]
    status = (await client.get(f"/api/v1/payments/{checkout['transaction_id']}", headers=auth(member))).json()
    assert status["status"] == "paid"
    assert status["gym_id"] == str(DISTRICT_1_GYM_ID)
    assert status["membership_status"] == "active"
    assert status["invoice_id"]

    sessions, _ = storage
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(UserMembership).where(UserMembership.user_id == member.id)) == 1
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == member.id))).scalar_one()
        assert membership.home_gym_id == DISTRICT_1_GYM_ID
        assert await session.scalar(select(func.count()).select_from(Invoice).where(Invoice.payment_id == checkout["transaction_id"])) == 1
        assert await session.scalar(select(func.count()).select_from(EmailDelivery).where(EmailDelivery.payment_id == checkout["transaction_id"])) == 1
        assert await session.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.entity_id == checkout["transaction_id"], AuditLog.action == "payment.payos.confirmed")) == 1


async def test_webhook_rejects_invalid_signature_and_amount_without_mutation(client, storage):
    plan, member, _ = await create_member_and_plan(storage)
    checkout = (await start_payment(client, plan, member)).json()
    invalid = await client.post(
        "/api/v1/payments/payos/webhook",
        json=webhook(checkout["order_code"], checkout["amount_vnd"], valid=False),
    )
    assert invalid.status_code == 400
    mismatch = await client.post(
        "/api/v1/payments/payos/webhook",
        json=webhook(checkout["order_code"], 1, reference="mismatch-ref"),
    )
    assert mismatch.status_code == 400
    sample = await client.post("/api/v1/payments/payos/webhook", json=webhook(123, 3000))
    assert sample.status_code == 200
    malformed_length = await client.post(
        "/api/v1/payments/payos/webhook",
        content=json.dumps(webhook(124, 3000)),
        headers={"content-type": "application/json", "content-length": "invalid"},
    )
    assert malformed_length.status_code == 200
    oversized = await client.post(
        "/api/v1/payments/payos/webhook",
        content=b"{}",
        headers={"content-type": "application/json", "content-length": "65537"},
    )
    assert oversized.status_code == 413

    sessions, _ = storage
    async with sessions() as session:
        payment = await session.get(Payment, checkout["transaction_id"])
        assert payment.status == "pending"
        assert await session.scalar(select(func.count()).select_from(Invoice)) == 0


async def create_paid_class_fixture(storage):
    sessions, _ = storage
    async with sessions() as session:
        members = [User(
            name=f"Class Member {index}",
            email=f"class-{index}-{uuid4().hex[:6]}@example.com",
            phone=f"07{uuid4().int % 100000000:08d}",
            password_hash="unused",
            is_email_verified=True,
        ) for index in range(2)]
        start = datetime.now(UTC) + timedelta(days=3)
        gym_class = GymClass(
            title="Independent Strength Session",
            class_type="Strength",
            start_at=start,
            end_at=start + timedelta(hours=1),
            capacity=2,
            price_vnd=150_000,
            location="Studio Paid",
            status="scheduled",
        )
        session.add_all([*members, gym_class])
        await session.commit()
    return gym_class, members


async def test_independent_class_payment_confirms_once_without_membership(client, storage):
    gym_class, members = await create_paid_class_fixture(storage)
    response = await client.post(
        f"/api/v1/classes/{gym_class.id}/checkout",
        headers=auth(members[0]),
        json={"idempotency_key": "class-payos-checkout", "client_platform": "web"},
    )
    assert response.status_code == 201, response.text
    checkout = response.json()
    assert checkout["amount_vnd"] == 150_000
    payload = webhook(checkout["order_code"], 150_000)
    assert (await client.post("/api/v1/payments/payos/webhook", json=payload)).status_code == 200
    assert (await client.post("/api/v1/payments/payos/webhook", json=payload)).status_code == 200

    sessions, _ = storage
    async with sessions() as session:
        booking = await session.get(ClassBooking, checkout["booking_id"])
        assert booking.status == "confirmed"
        assert await session.scalar(select(func.count()).select_from(UserMembership).where(UserMembership.user_id == members[0].id)) == 0
        assert await session.scalar(select(func.count()).select_from(Invoice).where(Invoice.payment_id == checkout["transaction_id"])) == 1
        assert await session.scalar(select(func.count()).select_from(EmailDelivery).where(EmailDelivery.payment_id == checkout["transaction_id"])) == 2


async def test_order_codes_are_unique_and_provider_failure_rolls_back(client, storage, monkeypatch):
    first_plan, first_member, _ = await create_member_and_plan(storage)
    second_plan, second_member, _ = await create_member_and_plan(storage)
    responses = await asyncio.gather(
        start_payment(client, first_plan, first_member),
        start_payment(client, second_plan, second_member),
    )
    assert all(response.status_code == 201 for response in responses)
    assert len({response.json()["order_code"] for response in responses}) == 2

    async def unavailable(*args, **kwargs):
        raise AppError("PAYOS_UNAVAILABLE", "Payment checkout is temporarily unavailable.", 503)

    monkeypatch.setattr(PayOSClient, "create_payment_link", unavailable)
    third_plan, third_member, _ = await create_member_and_plan(storage)
    failed = await start_payment(client, third_plan, third_member)
    assert failed.status_code == 503
    sessions, _ = storage
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Payment).where(Payment.user_id == third_member.id)) == 0


async def test_expired_payment_and_late_webhook_require_review(client, storage):
    plan, member, _ = await create_member_and_plan(storage)
    checkout = (await start_payment(client, plan, member)).json()
    sessions, _ = storage
    async with sessions() as session:
        payment = await session.get(Payment, checkout["transaction_id"])
        payment.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    async with sessions() as session:
        assert await PayOSPaymentService(session).expire_pending() == 1
    assert (await client.post(
        "/api/v1/payments/payos/webhook",
        json=webhook(checkout["order_code"], checkout["amount_vnd"]),
    )).status_code == 200
    status = (await client.get(f"/api/v1/payments/{checkout['transaction_id']}", headers=auth(member))).json()
    assert status["status"] == "paid_review"
    assert status["membership_status"] is None
