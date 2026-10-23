import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.billing import Invoice, Payment
from app.models.classes import ClassBooking, ClassWaitlist, GymClass
from app.models.email_delivery import EmailDelivery
from app.models.membership import MembershipPlan, UserMembership
from app.models.operations import AuditLog, Notification
from app.models.user import User
from app.services.payment_service import VNPayPaymentService
from app.services.vnpay_service import VNPaySigner
from app.utils.security import create_access_token


pytestmark = pytest.mark.asyncio

TEST_TMN_CODE = "TESTVNP1"
TEST_HASH_SECRET = "isolated-vnpay-test-secret"


async def create_member_and_plan(storage, *, with_membership: bool = False):
    sessions, _ = storage
    today = date.today()
    async with sessions() as session:
        plan = MembershipPlan(
            id=uuid4(),
            name=f"VNPay plan {uuid4().hex[:8]}",
            duration_months=1,
            duration_days=30,
            base_price=Decimal("720000"),
        )
        member = User(
            id=uuid4(),
            name="VNPay Member",
            email=f"vnpay-{uuid4().hex[:8]}@example.com",
            phone=f"09{uuid4().int % 100000000:08d}",
            password_hash="unused",
            is_email_verified=True,
        )
        other = User(
            id=uuid4(),
            name="Other Member",
            email=f"other-{uuid4().hex[:8]}@example.com",
            phone=f"08{uuid4().int % 100000000:08d}",
            password_hash="unused",
            is_email_verified=True,
        )
        session.add_all([plan, member, other])
        await session.flush()
        membership = None
        if with_membership:
            membership = UserMembership(
                user_id=member.id,
                plan_id=plan.id,
                status="active",
                start_date=today,
                expiry_date=today + timedelta(days=10),
            )
            session.add(membership)
        await session.commit()
        original_expiry = membership.expiry_date if membership else None

    token = create_access_token(user_id=member.id, role="member", tier="normal")[0]
    other_token = create_access_token(user_id=other.id, role="member", tier="normal")[0]
    return plan, member, {"Authorization": f"Bearer {token}"}, {"Authorization": f"Bearer {other_token}"}, original_expiry


def signed_ipn(*, txn_ref: str, amount: int = 72_000_000, response_code: str = "00", transaction_status: str = "00") -> dict[str, str]:
    parameters = {
        "vnp_Amount": str(amount),
        "vnp_BankCode": "NCB",
        "vnp_CardType": "ATM",
        "vnp_OrderInfo": f"YPGym membership {txn_ref}",
        "vnp_PayDate": "20260930153045",
        "vnp_ResponseCode": response_code,
        "vnp_TmnCode": TEST_TMN_CODE,
        "vnp_TransactionNo": f"9{uuid4().int % 100000000:08d}",
        "vnp_TransactionStatus": transaction_status,
        "vnp_TxnRef": txn_ref,
    }
    parameters["vnp_SecureHash"] = VNPaySigner(TEST_HASH_SECRET).sign(parameters)
    return parameters


async def start_payment(client, plan, headers, *, client_platform: str = "web"):
    response = await client.post(
        "/api/v1/payments/vnpay/create",
        headers=headers,
        json={"membership_plan_id": str(plan.id), "locale": "vn", "client_platform": client_platform},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_checkout_uses_server_price_and_return_cannot_activate_membership(client, storage):
    plan, _, headers, other_headers, _ = await create_member_and_plan(storage)

    rejected = await client.post(
        "/api/v1/payments/vnpay/create",
        headers=headers,
        json={"membership_plan_id": str(plan.id), "amount_vnd": 1},
    )
    assert rejected.status_code == 422

    checkout = await start_payment(client, plan, headers)
    payment_query = parse_qs(urlsplit(checkout["payment_url"]).query)
    assert payment_query["vnp_Amount"] == ["72000000"]
    assert payment_query["vnp_TmnCode"] == [TEST_TMN_CODE]
    assert len(payment_query["vnp_SecureHash"][0]) == 128
    assert TEST_HASH_SECRET not in checkout["payment_url"]

    forbidden = await client.get(f"/api/v1/payments/{checkout['transaction_id']}", headers=other_headers)
    assert forbidden.status_code == 404

    callback = signed_ipn(txn_ref=checkout["txn_ref"])
    returned = await client.get("/api/v1/payments/vnpay/return", params=callback, follow_redirects=False)
    assert returned.status_code == 302
    assert "state=processing" in returned.headers["location"]

    sessions, _ = storage
    async with sessions() as session:
        payment = await session.get(Payment, checkout["transaction_id"])
        assert payment.status == "pending"
        assert await session.scalar(select(func.count()).select_from(UserMembership)) == 0
        assert await session.scalar(select(func.count()).select_from(Invoice)) == 0


async def test_ipn_validates_signature_order_and_amount(client, storage):
    plan, _, headers, _, _ = await create_member_and_plan(storage)

    for invalid_payload in (
        {"membership_plan_id": str(uuid4())},
        {"membership_plan_id": str(plan.id), "locale": "fr"},
        {"membership_plan_id": str(plan.id), "bank_code": "UNSUPPORTED"},
    ):
        rejected = await client.post("/api/v1/payments/vnpay/create", headers=headers, json=invalid_payload)
        assert rejected.status_code in (404, 422)

    checkout = await start_payment(client, plan, headers)

    invalid = signed_ipn(txn_ref=checkout["txn_ref"])
    invalid["vnp_SecureHash"] = "0" * 128
    assert (await client.get("/api/v1/payments/vnpay/ipn", params=invalid)).json()["RspCode"] == "97"

    unknown = signed_ipn(txn_ref="UNKNOWN-ORDER")
    assert (await client.get("/api/v1/payments/vnpay/ipn", params=unknown)).json()["RspCode"] == "01"

    mismatch = signed_ipn(txn_ref=checkout["txn_ref"], amount=100)
    assert (await client.get("/api/v1/payments/vnpay/ipn", params=mismatch)).json()["RspCode"] == "04"

    status = await client.get(f"/api/v1/payments/{checkout['transaction_id']}", headers=headers)
    assert status.json()["status"] == "pending"

    incomplete_success = signed_ipn(txn_ref=checkout["txn_ref"], response_code="00", transaction_status="01")
    assert (await client.get("/api/v1/payments/vnpay/ipn", params=incomplete_success)).json()["RspCode"] == "00"
    assert (await client.get(f"/api/v1/payments/{checkout['transaction_id']}", headers=headers)).json()["status"] == "failed"


async def test_successful_ipn_is_atomic_and_replay_safe(client, storage):
    plan, member, headers, _, _ = await create_member_and_plan(storage)
    checkout = await start_payment(client, plan, headers)
    callback = signed_ipn(txn_ref=checkout["txn_ref"])

    responses = await asyncio.gather(
        client.get("/api/v1/payments/vnpay/ipn", params=callback),
        client.get("/api/v1/payments/vnpay/ipn", params=callback),
    )
    assert sorted(response.json()["RspCode"] for response in responses) == ["00", "02"]

    status = (await client.get(f"/api/v1/payments/{checkout['transaction_id']}", headers=headers)).json()
    assert status["status"] == "paid"
    assert status["membership_status"] == "active"
    assert status["invoice_id"]

    returned = await client.get("/api/v1/payments/vnpay/return", params=callback, follow_redirects=False)
    assert returned.status_code == 302
    assert "state=success" in returned.headers["location"]

    sessions, _ = storage
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(UserMembership).where(UserMembership.user_id == member.id)) == 1
        assert await session.scalar(select(func.count()).select_from(Invoice).where(Invoice.payment_id == checkout["transaction_id"])) == 1
        assert await session.scalar(select(func.count()).select_from(EmailDelivery).where(EmailDelivery.payment_id == checkout["transaction_id"])) == 1
        assert await session.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == member.id, Notification.notification_type == "membership_payment_confirmed")) == 1
        assert await session.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.entity_id == checkout["transaction_id"], AuditLog.action == "payment.vnpay.confirmed")) == 1


async def test_ipn_renews_existing_membership_and_handles_cancel_and_expiry(client, storage):
    plan, member, headers, _, original_expiry = await create_member_and_plan(storage, with_membership=True)
    renewal = await start_payment(client, plan, headers)
    renewed = await client.get("/api/v1/payments/vnpay/ipn", params=signed_ipn(txn_ref=renewal["txn_ref"]))
    assert renewed.json()["RspCode"] == "00"

    sessions, _ = storage
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == member.id))).scalar_one()
        assert membership.expiry_date == original_expiry + timedelta(days=plan.duration_days)

    cancelled = await start_payment(client, plan, headers)
    cancelled_ipn = signed_ipn(txn_ref=cancelled["txn_ref"], response_code="24", transaction_status="02")
    assert (await client.get("/api/v1/payments/vnpay/ipn", params=cancelled_ipn)).json()["RspCode"] == "00"
    assert (await client.get(f"/api/v1/payments/{cancelled['transaction_id']}", headers=headers)).json()["status"] == "cancelled"

    expiring = await start_payment(client, plan, headers)
    async with sessions() as session:
        payment = await session.get(Payment, expiring["transaction_id"])
        payment.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    expired = await client.get(f"/api/v1/payments/{expiring['transaction_id']}", headers=headers)
    assert expired.json()["status"] == "expired"


async def create_paid_class_fixture(storage, *, capacity: int = 2, member_count: int = 2):
    sessions, _ = storage
    async with sessions() as session:
        users = [
            User(
                id=uuid4(),
                name=f"Class Buyer {index}",
                email=f"class-buyer-{index}-{uuid4().hex[:6]}@example.com",
                phone=f"07{uuid4().int % 100000000:08d}",
                password_hash="unused",
                is_email_verified=True,
            )
            for index in range(member_count)
        ]
        staff = User(
            id=uuid4(),
            name="Class Staff",
            email=f"class-staff-{uuid4().hex[:6]}@example.com",
            phone=f"06{uuid4().int % 100000000:08d}",
            password_hash="unused",
            role="staff",
            is_email_verified=True,
        )
        start = datetime.now(UTC) + timedelta(days=3)
        gym_class = GymClass(
            id=uuid4(),
            title="Independent Strength Session",
            class_type="Strength",
            start_at=start,
            end_at=start + timedelta(hours=1),
            capacity=capacity,
            price_vnd=150_000,
            location="Studio Paid",
            status="scheduled",
        )
        session.add_all([*users, staff, gym_class])
        await session.commit()
    headers = [
        {"Authorization": f"Bearer {create_access_token(user_id=user.id, role='member', tier='normal')[0]}"}
        for user in users
    ]
    staff_header = {
        "Authorization": f"Bearer {create_access_token(user_id=staff.id, role='staff', tier='normal')[0]}"
    }
    return gym_class, users, headers, staff_header


async def start_class_payment(client, gym_class, headers, key: str):
    response = await client.post(
        f"/api/v1/classes/{gym_class.id}/checkout",
        headers=headers,
        json={"idempotency_key": key, "locale": "vn", "client_platform": "web"},
    )
    return response


async def test_non_member_class_purchase_is_independent_atomic_and_attendable(client, storage):
    gym_class, users, headers, staff_header = await create_paid_class_fixture(storage)
    visible = await client.get("/api/v1/classes/upcoming", headers=headers[0])
    assert visible.status_code == 200
    assert visible.json()["booking_eligible"] is True
    assert visible.json()["items"][0]["price_vnd"] == 150_000

    forged = await client.post(
        f"/api/v1/classes/{gym_class.id}/checkout",
        headers=headers[0],
        json={"idempotency_key": "forged-price", "amount_vnd": 1},
    )
    assert forged.status_code == 422
    checkout = await start_class_payment(client, gym_class, headers[0], "class-checkout-1")
    assert checkout.status_code == 201, checkout.text
    checkout = checkout.json()
    assert parse_qs(urlsplit(checkout["payment_url"]).query)["vnp_Amount"] == ["15000000"]

    replay = await start_class_payment(client, gym_class, headers[0], "class-checkout-1")
    assert replay.status_code == 201
    assert replay.json()["transaction_id"] == checkout["transaction_id"]

    sessions, _ = storage
    async with sessions() as session:
        stored_class = await session.get(GymClass, gym_class.id)
        stored_class.price_vnd = 225_000
        await session.commit()

    callback = signed_ipn(txn_ref=checkout["txn_ref"], amount=15_000_000)
    responses = await asyncio.gather(
        client.get("/api/v1/payments/vnpay/ipn", params=callback),
        client.get("/api/v1/payments/vnpay/ipn", params=callback),
    )
    assert sorted(response.json()["RspCode"] for response in responses) == ["00", "02"]
    status = (await client.get(f"/api/v1/payments/{checkout['transaction_id']}", headers=headers[0])).json()
    assert status["product_type"] == "class_booking"
    assert status["booking_status"] == "confirmed"
    assert status["invoice_id"]

    checked_in = await client.post(
        f"/api/v1/admin/classes/bookings/{checkout['booking_id']}/check-in",
        headers=staff_header,
    )
    assert checked_in.status_code == 200, checked_in.text
    assert checked_in.json()["attended_at"]

    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(UserMembership).where(UserMembership.user_id == users[0].id)) == 0
        invoice = (await session.execute(select(Invoice).where(Invoice.payment_id == checkout["transaction_id"]))).scalar_one()
        assert invoice.product_type == "class_booking"
        assert invoice.product_name == gym_class.title
        assert await session.scalar(select(func.count()).select_from(EmailDelivery).where(EmailDelivery.payment_id == checkout["transaction_id"])) == 2

    cancelled = await client.post(f"/api/v1/bookings/{checkout['booking_id']}/cancel", headers=headers[0])
    assert cancelled.status_code == 200
    assert cancelled.json()["refund_status"] == "required"


async def test_promoted_waitlist_member_can_start_checkout(client, storage):
    gym_class, _, headers, _ = await create_paid_class_fixture(storage, capacity=1)
    checkout = (await start_class_payment(client, gym_class, headers[0], "waitlist-seat-owner")).json()
    callback = signed_ipn(txn_ref=checkout["txn_ref"], amount=15_000_000)
    assert (await client.get("/api/v1/payments/vnpay/ipn", params=callback)).json()["RspCode"] == "00"

    joined = await client.post(f"/api/v1/classes/{gym_class.id}/waitlist", headers=headers[1])
    assert joined.status_code == 200, joined.text
    cancelled = await client.post(f"/api/v1/bookings/{checkout['booking_id']}/cancel", headers=headers[0])
    assert cancelled.status_code == 200, cancelled.text

    promoted_checkout = await start_class_payment(client, gym_class, headers[1], "promoted-member-checkout")
    assert promoted_checkout.status_code == 201, promoted_checkout.text
    assert promoted_checkout.json()["booking_id"]


async def test_failed_class_payment_promotes_waitlist_once(client, storage):
    gym_class, users, headers, _ = await create_paid_class_fixture(storage, capacity=1)
    checkout = (await start_class_payment(client, gym_class, headers[0], "failed-seat-owner")).json()
    joined = await client.post(f"/api/v1/classes/{gym_class.id}/waitlist", headers=headers[1])
    assert joined.status_code == 200, joined.text

    callback = signed_ipn(
        txn_ref=checkout["txn_ref"],
        amount=15_000_000,
        response_code="07",
        transaction_status="02",
    )
    assert (await client.get("/api/v1/payments/vnpay/ipn", params=callback)).json()["RspCode"] == "00"
    assert (await client.get("/api/v1/payments/vnpay/ipn", params=callback)).json()["RspCode"] == "02"

    sessions, _ = storage
    async with sessions() as session:
        failed_booking = await session.get(ClassBooking, checkout["booking_id"])
        promoted_waitlist = (
            await session.execute(
                select(ClassWaitlist).where(
                    ClassWaitlist.class_id == gym_class.id,
                    ClassWaitlist.user_id == users[1].id,
                )
            )
        ).scalar_one()
        promoted_booking = (
            await session.execute(
                select(ClassBooking).where(
                    ClassBooking.class_id == gym_class.id,
                    ClassBooking.user_id == users[1].id,
                )
            )
        ).scalar_one()
        notification_channels = list(
            (
                await session.execute(
                    select(Notification.channel).where(
                        Notification.user_id == users[1].id,
                        Notification.notification_type == "waitlist_promoted",
                    )
                )
            ).scalars()
        )
        assert failed_booking.status == "payment_failed"
        assert failed_booking.reserved_until is None
        assert promoted_waitlist.status == "promoted"
        assert promoted_booking.status == "pending_payment"
        assert sorted(notification_channels) == ["email", "in_app"]

    promoted_checkout = await start_class_payment(client, gym_class, headers[1], "after-failed-payment")
    assert promoted_checkout.status_code == 201, promoted_checkout.text


async def test_owner_status_expiry_promotes_waitlist(client, storage):
    gym_class, users, headers, _ = await create_paid_class_fixture(storage, capacity=1)
    checkout = (await start_class_payment(client, gym_class, headers[0], "expiring-seat-owner")).json()
    joined = await client.post(f"/api/v1/classes/{gym_class.id}/waitlist", headers=headers[1])
    assert joined.status_code == 200, joined.text

    sessions, _ = storage
    async with sessions() as session:
        payment = await session.get(Payment, checkout["transaction_id"])
        booking = await session.get(ClassBooking, checkout["booking_id"])
        expired_at = datetime.now(UTC) - timedelta(seconds=1)
        payment.expires_at = expired_at
        booking.reserved_until = expired_at
        await session.commit()

    status = await client.get(f"/api/v1/payments/{checkout['transaction_id']}", headers=headers[0])
    assert status.status_code == 200, status.text
    assert status.json()["status"] == "expired"
    assert status.json()["booking_status"] == "expired"

    async with sessions() as session:
        promoted_waitlist = (
            await session.execute(
                select(ClassWaitlist).where(
                    ClassWaitlist.class_id == gym_class.id,
                    ClassWaitlist.user_id == users[1].id,
                )
            )
        ).scalar_one()
        assert promoted_waitlist.status == "promoted"

    promoted_checkout = await start_class_payment(client, gym_class, headers[1], "after-status-expiry")
    assert promoted_checkout.status_code == 201, promoted_checkout.text


async def test_expiry_worker_promotes_waitlist(client, storage):
    gym_class, users, headers, _ = await create_paid_class_fixture(storage, capacity=1)
    checkout = (await start_class_payment(client, gym_class, headers[0], "worker-expiring-owner")).json()
    joined = await client.post(f"/api/v1/classes/{gym_class.id}/waitlist", headers=headers[1])
    assert joined.status_code == 200, joined.text

    sessions, _ = storage
    async with sessions() as session:
        payment = await session.get(Payment, checkout["transaction_id"])
        booking = await session.get(ClassBooking, checkout["booking_id"])
        expired_at = datetime.now(UTC) - timedelta(seconds=1)
        payment.expires_at = expired_at
        booking.reserved_until = expired_at
        await session.commit()

    async with sessions() as session:
        assert await VNPayPaymentService(session).expire_pending() == 1

    async with sessions() as session:
        payment = await session.get(Payment, checkout["transaction_id"])
        owner_booking = await session.get(ClassBooking, checkout["booking_id"])
        promoted_waitlist = (
            await session.execute(
                select(ClassWaitlist).where(
                    ClassWaitlist.class_id == gym_class.id,
                    ClassWaitlist.user_id == users[1].id,
                )
            )
        ).scalar_one()
        assert payment.status == "expired"
        assert owner_booking.status == "expired"
        assert promoted_waitlist.status == "promoted"


async def test_checkout_cleanup_preserves_waitlist_priority(client, storage):
    gym_class, users, headers, _ = await create_paid_class_fixture(storage, capacity=1, member_count=3)
    checkout = (await start_class_payment(client, gym_class, headers[0], "cleanup-expiring-owner")).json()
    joined = await client.post(f"/api/v1/classes/{gym_class.id}/waitlist", headers=headers[1])
    assert joined.status_code == 200, joined.text

    sessions, _ = storage
    async with sessions() as session:
        payment = await session.get(Payment, checkout["transaction_id"])
        booking = await session.get(ClassBooking, checkout["booking_id"])
        expired_at = datetime.now(UTC) - timedelta(seconds=1)
        payment.expires_at = expired_at
        booking.reserved_until = expired_at
        await session.commit()

    outsider = await start_class_payment(client, gym_class, headers[2], "cleanup-outsider")
    assert outsider.status_code == 409, outsider.text
    assert outsider.json()["error"]["code"] == "CLASS_FULL"

    async with sessions() as session:
        expired_payment = await session.get(Payment, checkout["transaction_id"])
        promoted_waitlist = (
            await session.execute(
                select(ClassWaitlist).where(
                    ClassWaitlist.class_id == gym_class.id,
                    ClassWaitlist.user_id == users[1].id,
                )
            )
        ).scalar_one()
        assert expired_payment.status == "expired"
        assert promoted_waitlist.status == "promoted"

    promoted_checkout = await start_class_payment(client, gym_class, headers[1], "after-checkout-cleanup")
    assert promoted_checkout.status_code == 201, promoted_checkout.text

    async with sessions() as session:
        payment = await session.get(Payment, checkout["transaction_id"])
        promoted_waitlist = (
            await session.execute(
                select(ClassWaitlist).where(
                    ClassWaitlist.class_id == gym_class.id,
                    ClassWaitlist.user_id == users[1].id,
                )
            )
        ).scalar_one()
        assert payment.status == "expired"
        assert promoted_waitlist.status == "promoted"


async def test_last_seat_race_and_late_paid_hold_require_resolution(client, storage):
    gym_class, _, headers, _ = await create_paid_class_fixture(storage, capacity=1)
    attempts = await asyncio.gather(
        start_class_payment(client, gym_class, headers[0], "last-seat-user-1"),
        start_class_payment(client, gym_class, headers[1], "last-seat-user-2"),
    )
    assert sorted(response.status_code for response in attempts) == [201, 409]
    winner = next(response.json() for response in attempts if response.status_code == 201)

    sessions, _ = storage
    async with sessions() as session:
        admin = User(
            name="Late Payment Admin",
            email=f"late-payment-admin-{uuid4().hex[:6]}@example.com",
            phone=f"03{uuid4().int % 100000000:08d}",
            password_hash="unused",
            role="admin",
            is_email_verified=True,
        )
        session.add(admin)
        payment = await session.get(Payment, winner["transaction_id"])
        booking = await session.get(ClassBooking, winner["booking_id"])
        payment.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        payment.status = "expired"
        booking.reserved_until = payment.expires_at
        booking.status = "expired"
        await session.commit()

    callback = signed_ipn(txn_ref=winner["txn_ref"], amount=15_000_000)
    assert (await client.get("/api/v1/payments/vnpay/ipn", params=callback)).json()["RspCode"] == "00"
    status = (await client.get(f"/api/v1/payments/{winner['transaction_id']}", headers=headers[0])).json()
    if status.get("class_booking_id") != winner["booking_id"]:
        status = (await client.get(f"/api/v1/payments/{winner['transaction_id']}", headers=headers[1])).json()
    assert status["status"] == "paid_review"
    assert status["booking_status"] == "expired"
    assert status["refund_status"] == "required"
    assert status["invoice_id"] is None

    admin_header = {
        "Authorization": f"Bearer {create_access_token(user_id=admin.id, role='admin', tier='normal')[0]}"
    }
    resolved = await client.post(
        f"/api/v1/payments/{winner['transaction_id']}/resolve-class-refund",
        headers=admin_header,
        json={"reason": "Late payment refunded in the VNPay merchant portal"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["booking_status"] == "refunded"
    assert resolved.json()["refund_status"] == "resolved"


async def test_staff_class_cancellation_flags_paid_booking_for_admin_resolution(client, storage):
    gym_class, _, headers, staff_header = await create_paid_class_fixture(storage)
    sessions, _ = storage
    async with sessions() as session:
        manager = User(
            name="Class Manager",
            email=f"class-manager-{uuid4().hex[:6]}@example.com",
            phone=f"05{uuid4().int % 100000000:08d}",
            password_hash="unused",
            role="manager",
            is_email_verified=True,
        )
        admin = User(
            name="Class Admin",
            email=f"class-admin-{uuid4().hex[:6]}@example.com",
            phone=f"04{uuid4().int % 100000000:08d}",
            password_hash="unused",
            role="admin",
            is_email_verified=True,
        )
        session.add_all([manager, admin])
        await session.commit()
    manager_header = {"Authorization": f"Bearer {create_access_token(user_id=manager.id, role='manager', tier='normal')[0]}"}
    admin_header = {"Authorization": f"Bearer {create_access_token(user_id=admin.id, role='admin', tier='normal')[0]}"}

    checkout = (await start_class_payment(client, gym_class, headers[0], "staff-cancel-paid-class")).json()
    callback = signed_ipn(txn_ref=checkout["txn_ref"], amount=15_000_000)
    assert (await client.get("/api/v1/payments/vnpay/ipn", params=callback)).json()["RspCode"] == "00"

    cancelled = await client.post(
        f"/api/v1/admin/classes/{gym_class.id}/cancel",
        headers=manager_header,
        json={"reason": "Instructor is unavailable"},
    )
    assert cancelled.status_code == 200, cancelled.text
    status = (await client.get(f"/api/v1/payments/{checkout['transaction_id']}", headers=headers[0])).json()
    assert status["booking_status"] == "cancelled"
    assert status["refund_status"] == "required"
    assert (await client.post(
        f"/api/v1/admin/classes/bookings/{checkout['booking_id']}/check-in",
        headers=staff_header,
    )).status_code == 409

    resolved = await client.post(
        f"/api/v1/payments/{checkout['transaction_id']}/resolve-class-refund",
        headers=admin_header,
        json={"reason": "Refund completed in VNPay merchant portal"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["booking_status"] == "refunded"
    assert resolved.json()["refund_status"] == "resolved"
