"""Package 11: short emailed verification code, resend and lockout."""
import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.models.auth_token import EmailVerification
from app.utils.security import hash_token

pytestmark = pytest.mark.asyncio

CODE = "123456"


def _payload(email: str, phone: str) -> dict:
    return {"name": "Code Member", "email": email, "phone": phone, "password": "Test-password-123"}


async def _register(client, monkeypatch, email="code@example.com", phone="123456701", code=CODE):
    monkeypatch.setattr("app.services.auth_service.generate_numeric_code", lambda: code)
    response = await client.post("/api/v1/auth/register", json=_payload(email, phone))
    assert response.status_code == 201
    return response


async def test_email_carries_the_code_and_never_a_loopback_or_custom_scheme_link(client, monkeypatch):
    delivered = []
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="test",
        EMAIL_DELIVERY_MODE="smtp",
        EMAIL_SENDER_ADDRESS="team@example.com",
        SMTP_HOST="smtp.example.com",
        FRONTEND_URL="http://localhost:5174",
    )
    monkeypatch.setattr("app.services.auth_service.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.auth_service.ConfiguredEmailTransport.send", lambda self, message: delivered.append(message))
    response = await _register(client, monkeypatch)
    assert response.json()["verification_email_sent"] is True
    message = delivered[0]
    plain = message.get_body(preferencelist=("plain",)).get_content()
    html_body = message.get_body(preferencelist=("html",)).get_content()
    assert CODE in plain and CODE in html_body
    assert "localhost" not in message.as_string()
    assert "ypgym://" not in message.as_string()


async def test_failed_delivery_is_reported_to_the_client(client, monkeypatch):
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="test",
        EMAIL_DELIVERY_MODE="smtp",
        EMAIL_SENDER_ADDRESS="team@example.com",
        SMTP_HOST="smtp.example.com",
        FRONTEND_URL="https://gym.example.com",
    )

    def fail(self, message):
        raise OSError("PRIVATE_SMTP_DETAIL")

    monkeypatch.setattr("app.services.auth_service.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.auth_service.ConfiguredEmailTransport.send", fail)
    response = await _register(client, monkeypatch)
    assert response.json()["verification_email_sent"] is False
    assert "PRIVATE_SMTP_DETAIL" not in response.text


async def test_correct_code_verifies_once_and_consumes_the_link(client, storage, monkeypatch):
    sessions, _ = storage
    link_token = "code-link-token-1234567890abcdef"
    monkeypatch.setattr("app.services.auth_service.generate_url_token", lambda: link_token)
    await _register(client, monkeypatch)
    credentials = {"email": "code@example.com", "password": "Test-password-123"}
    assert (await client.post("/api/v1/auth/login", json=credentials)).status_code == 403
    verified = await client.post("/api/v1/auth/verify-email/code", json={"email": "code@example.com", "code": CODE})
    assert verified.status_code == 200
    assert verified.json()["user"]["is_email_verified"] is True
    assert (await client.post("/api/v1/auth/login", json=credentials)).status_code == 200
    async with sessions() as session:
        row = (await session.execute(select(EmailVerification))).scalar_one()
        assert row.used_at is not None
        assert row.code_hash and CODE not in row.code_hash
        assert row.token_hash == hash_token(link_token)
    assert "already verified" in (await client.get("/api/v1/auth/verify-email", params={"token": link_token})).json()["message"].lower()
    again = await client.post("/api/v1/auth/verify-email/code", json={"email": "code@example.com", "code": CODE})
    assert again.status_code == 400 and again.json()["error"]["code"] == "INVALID_VERIFICATION_CODE"


async def test_five_wrong_codes_lock_until_a_new_code_is_requested(client, storage, monkeypatch):
    _, redis = storage
    await _register(client, monkeypatch)
    for attempt in range(4):
        wrong = await client.post("/api/v1/auth/verify-email/code", json={"email": "code@example.com", "code": "000000"})
        assert wrong.status_code == 400 and wrong.json()["error"]["code"] == "INVALID_VERIFICATION_CODE"
    fifth = await client.post("/api/v1/auth/verify-email/code", json={"email": "code@example.com", "code": "000000"})
    assert fifth.status_code == 429 and fifth.json()["error"]["code"] == "VERIFICATION_CODE_LOCKED"
    correct_but_locked = await client.post("/api/v1/auth/verify-email/code", json={"email": "code@example.com", "code": CODE})
    assert correct_but_locked.status_code == 429
    await redis.flushdb()
    monkeypatch.setattr("app.services.auth_service.generate_numeric_code", lambda: "654321")
    assert (await client.post("/api/v1/auth/verify-email/resend", json={"email": "code@example.com"})).status_code == 200
    old = await client.post("/api/v1/auth/verify-email/code", json={"email": "code@example.com", "code": CODE})
    assert old.status_code == 400
    fresh = await client.post("/api/v1/auth/verify-email/code", json={"email": "code@example.com", "code": "654321"})
    assert fresh.status_code == 200


async def test_resend_response_is_identical_for_unknown_accounts_and_cooldown_applies_to_all(client, storage, monkeypatch):
    _, redis = storage
    await _register(client, monkeypatch)
    known = await client.post("/api/v1/auth/verify-email/resend", json={"email": "code@example.com"})
    unknown = await client.post("/api/v1/auth/verify-email/resend", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    for email in ("code@example.com", "nobody@example.com"):
        cooled = await client.post("/api/v1/auth/verify-email/resend", json={"email": email})
        assert cooled.status_code == 429
        assert cooled.json()["error"]["code"] == "RATE_LIMITED"
    await redis.flushdb()


async def test_expired_code_is_rejected_and_a_malformed_code_is_a_validation_error(client, storage, monkeypatch):
    sessions, _ = storage
    await _register(client, monkeypatch)
    async with sessions() as session:
        row = (await session.execute(select(EmailVerification))).scalar_one()
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()
    expired = await client.post("/api/v1/auth/verify-email/code", json={"email": "code@example.com", "code": CODE})
    assert expired.status_code == 400 and expired.json()["error"]["code"] == "VERIFICATION_TOKEN_EXPIRED"
    assert (await client.post("/api/v1/auth/verify-email/code", json={"email": "code@example.com", "code": "12ab56"})).status_code == 422


async def test_email_change_links_still_work(client, storage, monkeypatch):
    sessions, _ = storage
    await _register(client, monkeypatch)
    token = "email-change-token-1234567890abcdef"
    async with sessions() as session:
        from app.models.user import User

        user = (await session.execute(select(User).where(User.email == "code@example.com"))).scalar_one()
        session.add(EmailVerification(user_id=user.id, token_hash=hash_token(token), expires_at=datetime.now(UTC) + timedelta(hours=1), new_email="changed@example.com"))
        await session.commit()
    assert (await client.get("/api/v1/auth/verify-email", params={"token": token})).status_code == 200
    async with sessions() as session:
        user = (await session.execute(select(User).where(User.email == "changed@example.com"))).scalar_one()
        assert user.is_email_verified is True
