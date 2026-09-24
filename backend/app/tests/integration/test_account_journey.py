from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from mailbox import Maildir
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.core.exceptions import DependencyUnavailableError
from app.core.config import Settings
from app.models.auth_token import EmailVerification, PasswordReset
from app.models.billing import Invoice, Payment
from app.models.membership import MembershipPlan
from app.models.membership import UserMembership
from app.models.operations import AuditLog, Notification
from app.models.user import User
from app.services.email_service import EmailDeliveryService
from app.utils.security import create_access_token, hash_token

pytestmark = pytest.mark.asyncio


async def test_registration_verification_login_and_one_time_reset(client, storage, monkeypatch):
    sessions, _ = storage
    verification = "test-verification-material-123456"
    reset = "test-reset-material-1234567890123"
    monkeypatch.setattr("app.services.auth_service.generate_url_token", lambda: verification)
    payload = {"name": "Test member", "email": "journey@example.com", "phone": "123456789", "password": "Test-password-123"}
    registered = await client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 201
    assert "password" not in registered.text and verification not in registered.text
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 409
    assert (await client.post("/api/v1/auth/register", json={**payload, "email": "second@example.com"})).status_code == 409
    credentials = {"email": payload["email"], "password": payload["password"]}
    assert (await client.post("/api/v1/auth/login", json=credentials)).status_code == 403
    async with sessions() as session:
        row = (await session.execute(select(EmailVerification))).scalar_one()
        assert row.token_hash == hash_token(verification)
    assert (await client.get("/api/v1/auth/verify-email", params={"token": verification})).status_code == 200
    login = await client.post("/api/v1/auth/login", json=credentials)
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await client.get("/api/v1/auth/me", headers=headers)).json()["email"] == payload["email"]
    monkeypatch.setattr("app.services.auth_service.generate_url_token", lambda: reset)
    existing = await client.post("/api/v1/auth/forgot-password", json={"email": payload["email"]})
    missing = await client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.com"})
    assert existing.json() == missing.json()
    async with sessions() as session:
        record = (await session.execute(select(PasswordReset))).scalar_one()
        assert record.token_hash == hash_token(reset)
    reset_payload = {"token": reset, "new_password": "New-test-password-123"}
    assert (await client.post("/api/v1/auth/reset-password", json=reset_payload)).status_code == 200
    assert (await client.post("/api/v1/auth/reset-password", json=reset_payload)).status_code == 400
    assert (await client.post("/api/v1/auth/login", json=credentials)).status_code == 401
    assert (await client.post("/api/v1/auth/login", json={**credentials, "password": reset_payload["new_password"]})).status_code == 200


async def test_registration_queues_and_delivers_one_escaped_welcome_email(client, storage, monkeypatch, tmp_path):
    sessions, _ = storage
    monkeypatch.setattr("app.services.auth_service.generate_url_token", lambda: "welcome-verification-token-123456")
    payload = {
        "name": "<script>Member</script>",
        "email": "welcome@example.com",
        "phone": "123456780",
        "password": "Test-password-123",
    }

    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 409

    async with sessions() as session:
        queued = list(
            (
                await session.execute(
                    select(Notification).where(Notification.notification_type == "registration_welcome"),
                )
            ).scalars(),
        )
        assert len(queued) == 1
        assert queued[0].delivery_state == "pending"
        assert queued[0].delivery_attempts == 0
        assert queued[0].dedupe_key == f"registration-welcome:{queued[0].user_id}:email"

        settings = SimpleNamespace(
            EMAIL_DELIVERY_MODE="development",
            EMAIL_DELIVERY_BATCH_SIZE=25,
            EMAIL_MAX_DELIVERY_ATTEMPTS=5,
            EMAIL_RETRY_DELAY_SECONDS=300,
            EMAIL_SENDER_NAME="YPGym Team",
            EMAIL_SENDER_ADDRESS="no-reply@example.com",
            FRONTEND_URL="http://frontend.test",
            DEVELOPMENT_MAIL_DIR=str(tmp_path / "mail"),
        )
        service = EmailDeliveryService(session, settings=settings)
        assert await service.deliver_pending_welcome_emails() == 1
        assert await service.deliver_pending_welcome_emails() == 0

        delivered = (
            await session.execute(
                select(Notification).where(Notification.notification_type == "registration_welcome"),
            )
        ).scalar_one()
        assert delivered.delivery_state == "delivered"
        assert delivered.delivery_attempts == 1
        assert delivered.delivered_at is not None

    outbox = Maildir(tmp_path / "mail", create=False)
    try:
        messages = list(outbox.values())
        assert len(messages) == 1
        message = BytesParser(policy=policy.default).parsebytes(messages[0].as_bytes())
        assert message["From"] == "YPGym Team <no-reply@example.com>"
        assert message["To"] == payload["email"]
        assert message["Subject"] == "Welcome to YPGym"
        assert message["Message-ID"].startswith("<registration-welcome.")
        assert "http://frontend.test/login" in message.get_body(preferencelist=("plain",)).get_content()
        html_body = message.get_body(preferencelist=("html",)).get_content()
        assert "<script>Member</script>" not in html_body
        assert "&lt;script&gt;Member&lt;/script&gt;" in html_body
        assert "welcome-verification-token-123456" not in message.as_string()
    finally:
        outbox.close()


async def test_smtp_mode_delivers_the_one_time_verification_link(client, storage, monkeypatch):
    sessions, _ = storage
    delivered_messages = []

    def record_delivery(self, message):
        delivered_messages.append(message)

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="test",
        EMAIL_DELIVERY_MODE="smtp",
        EMAIL_SENDER_ADDRESS="team@example.com",
        SMTP_HOST="smtp.example.com",
        FRONTEND_URL="https://gym.example.com",
        MOBILE_APP_URL="ypgym://",
    )
    monkeypatch.setattr("app.services.auth_service.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.auth_service.ConfiguredEmailTransport.send", record_delivery)

    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "SMTP Member",
            "email": "smtp-member@example.com",
            "phone": "123456782",
            "password": "Test-password-123",
        },
    )
    assert registered.status_code == 201
    assert len(delivered_messages) == 1
    message = delivered_messages[0]
    assert message["From"] == "YPGym Team <team@example.com>"
    assert message["To"] == "smtp-member@example.com"
    links = message.get_content().splitlines()
    assert links[0].startswith("https://gym.example.com/verify-email?token=")
    assert links[1].startswith("ypgym://verify-email?token=")
    token = parse_qs(urlsplit(links[0]).query)["token"][0]
    assert parse_qs(urlsplit(links[1]).query)["token"] == [token]
    async with sessions() as session:
        row = (await session.execute(select(EmailVerification))).scalar_one()
        assert row.token_hash == hash_token(token)
        assert token not in row.token_hash
    assert (await client.get("/api/v1/auth/verify-email", params={"token": token})).status_code == 200


async def test_welcome_delivery_failure_is_private_and_retryable(client, storage, monkeypatch, caplog):
    sessions, _ = storage
    monkeypatch.setattr("app.services.auth_service.generate_url_token", lambda: "retry-verification-token-1234567")

    async def unavailable_verification_outbox(*args, **kwargs):
        raise DependencyUnavailableError(
            "EMAIL_PREPARATION_UNAVAILABLE",
            "PRIVATE_VERIFICATION_OUTBOX_DETAIL",
        )

    monkeypatch.setattr(
        "app.services.auth_service.AuthService._prepare_development_email",
        unavailable_verification_outbox,
    )
    payload = {
        "name": "Retry Member",
        "email": "retry-welcome@example.com",
        "phone": "123456781",
        "password": "Test-password-123",
    }
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    assert "PRIVATE_VERIFICATION_OUTBOX_DETAIL" not in caplog.text

    class FailingTransport:
        def send(self, message):
            raise OSError("PRIVATE_SMTP_CREDENTIAL_DETAIL")

    class RecordingTransport:
        def __init__(self):
            self.messages = []

        def send(self, message):
            self.messages.append(message)

    settings = SimpleNamespace(
        EMAIL_DELIVERY_BATCH_SIZE=25,
        EMAIL_MAX_DELIVERY_ATTEMPTS=5,
        EMAIL_RETRY_DELAY_SECONDS=300,
        EMAIL_SENDER_NAME="YPGym Team",
        EMAIL_SENDER_ADDRESS="no-reply@example.com",
        FRONTEND_URL="http://frontend.test",
    )
    async with sessions() as session:
        failed_service = EmailDeliveryService(session, settings=settings, transport=FailingTransport())
        assert await failed_service.deliver_pending_welcome_emails() == 0
        notification = (
            await session.execute(
                select(Notification).where(Notification.notification_type == "registration_welcome"),
            )
        ).scalar_one()
        assert notification.delivery_state == "pending"
        assert notification.delivery_attempts == 1
        assert "PRIVATE_SMTP_CREDENTIAL_DETAIL" not in caplog.text
        assert "exception_type=OSError" in caplog.text

        notification.last_delivery_attempt_at = datetime.now(UTC) - timedelta(seconds=301)
        await session.commit()
        transport = RecordingTransport()
        retry_service = EmailDeliveryService(session, settings=settings, transport=transport)
        assert await retry_service.deliver_pending_welcome_emails() == 1
        assert len(transport.messages) == 1
        await session.refresh(notification)
        assert notification.delivery_state == "delivered"
        assert notification.delivery_attempts == 2


async def test_welcome_email_stops_after_configured_failure_limit(client, storage, monkeypatch):
    sessions, _ = storage
    monkeypatch.setattr("app.services.auth_service.generate_url_token", lambda: "max-attempt-token-123456789012")
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Delivery limit",
            "email": "limit@example.com",
            "phone": "123456783",
            "password": "Test-password-123",
        },
    )
    assert response.status_code == 201

    class FailingTransport:
        def __init__(self):
            self.calls = 0

        def send(self, message):
            self.calls += 1
            raise OSError("smtp unavailable")

    transport = FailingTransport()
    settings = SimpleNamespace(
        EMAIL_DELIVERY_BATCH_SIZE=25,
        EMAIL_MAX_DELIVERY_ATTEMPTS=1,
        EMAIL_RETRY_DELAY_SECONDS=300,
        EMAIL_SENDER_NAME="YPGym Team",
        EMAIL_SENDER_ADDRESS="no-reply@example.com",
        FRONTEND_URL="http://frontend.test",
    )
    async with sessions() as session:
        service = EmailDeliveryService(session, settings=settings, transport=transport)
        assert await service.deliver_pending_welcome_emails() == 0
        assert await service.deliver_pending_welcome_emails() == 0
        notification = (
            await session.execute(
                select(Notification).where(Notification.notification_type == "registration_welcome"),
            )
        ).scalar_one()
        assert notification.delivery_state == "skipped"
        assert notification.delivery_attempts == 1
        assert transport.calls == 1


async def test_purchase_renewal_idempotency_invoice_and_ownership(client, storage):
    sessions, _ = storage
    async with sessions() as session:
        user = User(name="Buyer", email="buyer@example.com", phone="123456789", password_hash="unused", is_email_verified=True)
        other = User(name="Other", email="other@example.com", phone="987654321", password_hash="unused", is_email_verified=True)
        plan = MembershipPlan(name="Test monthly", duration_months=1, duration_days=30, base_price=Decimal("720000"), discount_percent=Decimal("5"))
        session.add_all([user, other, plan])
        await session.commit()
    token, _ = create_access_token(user_id=user.id, role="member", tier="normal")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"plan_id": str(plan.id), "idempotency_key": "purchase-test-1", "mock_payment_confirmed": False}
    assert (await client.post("/api/v1/memberships/purchase", json=payload, headers=headers)).status_code == 400
    payload["mock_payment_confirmed"] = True
    response = await client.post("/api/v1/memberships/purchase", json=payload, headers=headers)
    assert response.status_code == 200
    first = response.json()
    assert Decimal(first["payment"]["amount"]) == Decimal("684000")
    duplicate = (await client.post("/api/v1/memberships/purchase", json=payload, headers=headers)).json()
    assert duplicate["payment"]["id"] == first["payment"]["id"]
    renewal = (await client.post("/api/v1/memberships/purchase", json={**payload, "idempotency_key": "purchase-test-2"}, headers=headers)).json()
    assert date.fromisoformat(renewal["membership"]["expiry_date"]) == date.fromisoformat(first["membership"]["expiry_date"]) + timedelta(days=30)
    invoice_path = first["invoice"]["download_url"]
    pdf = await client.get(invoice_path, headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    other_token, _ = create_access_token(user_id=other.id, role="member", tier="normal")
    assert (await client.get(invoice_path, headers={"Authorization": f"Bearer {other_token}"})).status_code == 404
    async with sessions() as session:
        assert (await session.execute(select(func.count(Payment.id)))).scalar_one() == 2
        assert (await session.execute(select(func.count(Invoice.id)))).scalar_one() == 2
        invoice = await session.get(Invoice, UUID(first["invoice"]["id"]))
        assert invoice.membership_expiry_date == date.fromisoformat(first["membership"]["expiry_date"])


async def test_manager_can_manually_enroll_member_and_audit_action(client, storage):
    sessions, _ = storage
    async with sessions() as session:
        member = User(name="Reception member", email="reception-member@example.com", phone="123450000", password_hash="unused", is_email_verified=False)
        manager = User(name="Reception manager", email="reception-manager@example.com", phone="123450001", password_hash="unused", role="manager", is_email_verified=True)
        plan = MembershipPlan(name="Reception monthly", duration_months=1, duration_days=30, base_price=Decimal("500000"), discount_percent=Decimal("0"))
        session.add_all([member, manager, plan])
        await session.commit()
    manager_token, _ = create_access_token(user_id=manager.id, role="manager", tier=manager.tier)
    response = await client.post(
        f"/api/v1/admin/members/{member.id}/membership",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"plan_id": str(plan.id), "idempotency_key": "reception-enrollment-1", "reason": "Paid at reception during assisted signup"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Membership manually enrolled successfully."
    async with sessions() as session:
        membership = (await session.execute(select(UserMembership).where(UserMembership.user_id == member.id))).scalar_one()
        audit = (await session.execute(select(AuditLog).where(AuditLog.action == "membership.manual_enrollment.created", AuditLog.target_user_id == member.id))).scalar_one()
        assert membership.status == "active" and audit.actor_user_id == manager.id
