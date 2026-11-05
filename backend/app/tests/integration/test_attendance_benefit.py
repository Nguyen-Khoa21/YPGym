import asyncio
import hashlib
import hmac
import math
from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models.attendance import AttendanceSession
from app.models.billing import Invoice, Payment
from app.models.membership import MembershipPlan, UserMembership
from app.models.user import User
from app.services.membership_service import MembershipService
from app.services.payos_service import PayOSClient
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
        )

    monkeypatch.setattr(PayOSClient, "create_payment_link", create_payment_link)


def previous_month() -> tuple[date, date]:
    local_today = datetime.now(UTC).astimezone(ZoneInfo(get_settings().GYM_TIMEZONE)).date()
    period_start, period_end, _ = MembershipService.previous_complete_month(local_today)
    return period_start, period_end


async def create_fixture(storage, *, plan_discount: str = "5", membership_status: str = "active"):
    sessions, _ = storage
    period_start, _ = previous_month()
    qualifying_days = math.ceil(monthrange(period_start.year, period_start.month)[1] * 0.8)
    timezone = ZoneInfo(get_settings().GYM_TIMEZONE)
    async with sessions() as session:
        plan = MembershipPlan(
            name=f"Attendance plan {uuid4().hex[:8]}",
            duration_months=3,
            duration_days=90,
            base_price=Decimal("720000"),
            discount_percent=Decimal(plan_discount),
        )
        member = User(
            name="Attendance Member",
            email=f"attendance-{uuid4().hex[:8]}@example.com",
            phone=f"09{uuid4().int % 100000000:08d}",
            password_hash="unused",
            is_email_verified=True,
        )
        other = User(
            name="Other Attendance Member",
            email=f"attendance-other-{uuid4().hex[:8]}@example.com",
            phone=f"08{uuid4().int % 100000000:08d}",
            password_hash="unused",
            is_email_verified=True,
        )
        session.add_all([plan, member, other])
        await session.flush()
        today = datetime.now(UTC).astimezone(timezone).date()
        session.add(UserMembership(
            user_id=member.id,
            plan_id=plan.id,
            status=membership_status,
            start_date=today - timedelta(days=30),
            expiry_date=today + timedelta(days=30),
        ))
        for offset in range(qualifying_days):
            checked_in = datetime.combine(period_start + timedelta(days=offset), time(12), timezone).astimezone(UTC)
            session.add(AttendanceSession(user_id=member.id, checked_in_at=checked_in, status="checked_out", source="iot_scanner"))
        duplicate = datetime.combine(period_start, time(18), timezone).astimezone(UTC)
        session.add_all([
            AttendanceSession(user_id=member.id, checked_in_at=duplicate, status="checked_out", source="iot_scanner"),
            AttendanceSession(user_id=member.id, checked_in_at=duplicate, status="checked_out", source="staff_console"),
            AttendanceSession(user_id=other.id, checked_in_at=duplicate, status="checked_out", source="iot_scanner"),
        ])
        await session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(user_id=member.id, role='member', tier='normal')[0]}"}
    other_headers = {"Authorization": f"Bearer {create_access_token(user_id=other.id, role='member', tier='normal')[0]}"}
    return plan, member, headers, other_headers, qualifying_days


def signed_webhook(*, order_code: int, amount_vnd: int) -> dict:
    data = {
        "orderCode": order_code,
        "amount": amount_vnd,
        "description": f"YPG{order_code % 1_000_000:06d}",
        "accountNumber": "masked",
        "reference": f"ref-{order_code}",
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
    signature = hmac.new(b"isolated-checksum-key", message.encode(), hashlib.sha256).hexdigest()
    return {"code": "00", "desc": "success", "success": True, "data": data, "signature": signature}


async def start_checkout(client, plan, headers):
    return await client.post(
        "/api/v1/payments/payos/create",
        headers=headers,
        json={"membership_plan_id": str(plan.id), "client_platform": "web"},
    )


async def test_threshold_better_of_reservation_failure_release_and_consumption(client, storage):
    plan, member, headers, other_headers, qualifying_days = await create_fixture(storage)
    quote = (await client.get(
        "/api/v1/memberships/attendance-benefit/me",
        headers=headers,
        params={"plan_id": str(plan.id)},
    )).json()
    assert quote["attended_days"] == qualifying_days
    assert quote["attendance_qualified"] is True
    assert quote["status"] == "eligible"
    assert quote["pricing"]["plan_discount_percent"] == "5.00"
    assert quote["pricing"]["applied_discount_percent"] == "10.00"
    assert quote["pricing"]["final_amount"] == "648000.00"

    other_quote = (await client.get(
        "/api/v1/memberships/attendance-benefit/me",
        headers=other_headers,
        params={"plan_id": str(plan.id)},
    )).json()
    assert other_quote["attended_days"] == 1
    assert other_quote["status"] == "not_qualified"

    first = await start_checkout(client, plan, headers)
    assert first.status_code == 201, first.text
    first = first.json()
    assert first["amount_vnd"] == 648_000
    pending = await start_checkout(client, plan, headers)
    assert pending.status_code == 409
    assert pending.json()["error"]["code"] == "ATTENDANCE_BENEFIT_PENDING"

    sessions, _ = storage
    async with sessions() as session:
        payment = await session.get(Payment, first["transaction_id"])
        payment.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    failed = await client.get(f"/api/v1/payments/{first['transaction_id']}", headers=headers)
    assert failed.json()["status"] == "expired"
    assert (await client.get(
        "/api/v1/memberships/attendance-benefit/me",
        headers=headers,
        params={"plan_id": str(plan.id)},
    )).json()["status"] == "eligible"

    second = (await start_checkout(client, plan, headers)).json()
    settled = await client.post(
        "/api/v1/payments/payos/webhook",
        json=signed_webhook(order_code=second["order_code"], amount_vnd=648_000),
    )
    assert settled.status_code == 200
    consumed = (await client.get(
        "/api/v1/memberships/attendance-benefit/me",
        headers=headers,
        params={"plan_id": str(plan.id)},
    )).json()
    assert consumed["status"] == "consumed"
    assert consumed["pricing"]["applied_discount_percent"] == "5.00"
    assert consumed["pricing"]["final_amount"] == "684000.00"

    async with sessions() as session:
        payment = await session.get(Payment, second["transaction_id"])
        invoice = (await session.execute(select(Invoice).where(Invoice.payment_id == payment.id))).scalar_one()
        assert payment.attendance_benefit_period_start == previous_month()[0]
        assert payment.discount_details["pricing"]["rule"] == "better_of"
        assert invoice.discount_details == payment.discount_details
        assert payment.membership_id is not None


async def test_higher_plan_discount_wins_and_concurrent_checkout_reserves_once(client, storage):
    plan, _, headers, _, qualifying_days = await create_fixture(storage, plan_discount="15")
    quote = (await client.get(
        "/api/v1/memberships/attendance-benefit/me",
        headers=headers,
        params={"plan_id": str(plan.id)},
    )).json()
    assert quote["attended_days"] == qualifying_days
    assert quote["available"] is True
    assert quote["pricing"]["attendance_benefit_selected"] is False
    assert quote["pricing"]["applied_discount_percent"] == "15.00"
    assert quote["pricing"]["final_amount"] == "612000.00"

    attempts = await asyncio.gather(start_checkout(client, plan, headers), start_checkout(client, plan, headers))
    assert sorted(response.status_code for response in attempts) == [201, 409]
    winner = next(response.json() for response in attempts if response.status_code == 201)
    assert winner["amount_vnd"] == 612_000
    settled = await client.post(
        "/api/v1/payments/payos/webhook",
        json=signed_webhook(order_code=winner["order_code"], amount_vnd=612_000),
    )
    assert settled.status_code == 200
    consumed = (await client.get(
        "/api/v1/memberships/attendance-benefit/me",
        headers=headers,
        params={"plan_id": str(plan.id)},
    )).json()
    assert consumed["status"] == "consumed"
    assert consumed["pricing"]["applied_discount_percent"] == "15.00"


async def test_mock_renewal_applies_once_and_snapshots_invoice(client, storage):
    plan, _, headers, _, _ = await create_fixture(storage)
    payload = {
        "plan_id": str(plan.id),
        "idempotency_key": f"attendance-mock-{uuid4()}",
        "mock_payment_confirmed": True,
    }
    first = await client.post("/api/v1/memberships/purchase", headers=headers, json=payload)
    duplicate = await client.post("/api/v1/memberships/purchase", headers=headers, json=payload)
    assert first.status_code == duplicate.status_code == 200
    assert first.json()["payment"]["amount"] == "648000.00"
    assert duplicate.json()["payment"]["id"] == first.json()["payment"]["id"]

    sessions, _ = storage
    async with sessions() as session:
        payment = await session.get(Payment, first.json()["payment"]["id"])
        invoice = (await session.execute(select(Invoice).where(Invoice.payment_id == payment.id))).scalar_one()
        assert payment.attendance_benefit_period_start == previous_month()[0]
        assert payment.discount_details["pricing"]["applied_discount_percent"] == "10.00"
        assert invoice.discount_details == payment.discount_details


async def test_below_threshold_and_non_active_membership_do_not_apply_benefit(client, storage):
    plan, member, headers, _, qualifying_days = await create_fixture(storage, membership_status="frozen")
    frozen = (await client.get(
        "/api/v1/memberships/attendance-benefit/me",
        headers=headers,
        params={"plan_id": str(plan.id)},
    )).json()
    assert frozen["attended_days"] == qualifying_days
    assert frozen["status"] == "not_renewal"
    assert frozen["pricing"]["attendance_discount_percent"] == "0.00"

    sessions, _ = storage
    async with sessions() as session:
        await session.execute(
            AttendanceSession.__table__.delete().where(AttendanceSession.user_id == member.id),
        )
        await session.commit()
    zero = (await client.get(
        "/api/v1/memberships/attendance-benefit/me",
        headers=headers,
        params={"plan_id": str(plan.id)},
    )).json()
    assert zero["attended_days"] == 0
    assert zero["status"] == "not_qualified"

    async with sessions() as session:
        period_start, _ = previous_month()
        timezone = ZoneInfo(get_settings().GYM_TIMEZONE)
        for offset in range(qualifying_days - 1):
            checked_in = datetime.combine(period_start + timedelta(days=offset), time(12), timezone).astimezone(UTC)
            session.add(AttendanceSession(user_id=member.id, checked_in_at=checked_in, status="checked_out", source="iot_scanner"))
        await session.commit()
    below = (await client.get(
        "/api/v1/memberships/attendance-benefit/me",
        headers=headers,
        params={"plan_id": str(plan.id)},
    )).json()
    assert below["attended_days"] == qualifying_days - 1
    assert below["status"] == "not_qualified"
