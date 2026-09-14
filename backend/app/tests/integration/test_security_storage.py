import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from jose import jwt
from redis.exceptions import ConnectionError

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.rate_limit import rate_limits
from app.db.redis import get_redis_client
from app.models.attendance import IoTDevice
from app.models.user import User
from app.utils.security import create_access_token, hash_token

pytestmark = pytest.mark.asyncio


async def test_rate_counter_is_atomic_bounded_and_recovers_missing_expiry(storage):
    _, redis = storage
    async def attempt():
        try:
            await rate_limits.enforce(redis, key="test:race", limit=10, window_seconds=60)
            return 200
        except AppError as error:
            return error.status_code
    results = await asyncio.gather(*(attempt() for _ in range(100)))
    assert results.count(200) == 10
    assert results.count(429) == 90
    assert await redis.get("test:race") == "10"
    assert 0 < await redis.ttl("test:race") <= 60
    await redis.persist("test:race")
    assert await attempt() == 429
    assert 0 < await redis.ttl("test:race") <= 60
    await redis.pexpire("test:race", 1)
    await asyncio.sleep(0.02)
    assert await attempt() == 200


async def test_changing_email_cannot_bypass_login_ip_limit(client):
    for index in range(60):
        result = await client.post("/api/v1/auth/login", json={"email": f"missing{index}@example.com", "password": "invalid"})
        assert result.status_code == 401
    result = await client.post("/api/v1/auth/login", json={"email": "new@example.com", "password": "invalid"})
    assert result.status_code == 429
    assert int(result.headers["Retry-After"]) > 0


async def test_forgot_password_limit_and_neutral_response(client):
    for _ in range(5):
        result = await client.post("/api/v1/auth/forgot-password", json={"email": "absent@example.com"})
        assert result.status_code == 200
    assert (await client.post("/api/v1/auth/forgot-password", json={"email": "absent@example.com"})).status_code == 429


async def test_invalid_scanner_key_cannot_exhaust_authenticated_device_budget(client, storage):
    sessions, redis = storage
    async with sessions() as session:
        session.add(IoTDevice(device_id="test-gate", display_name="Test gate", api_key_hash=hash_token("valid-test-key")))
        await session.commit()
    payload = {"device_id": "test-gate", "qr_token": "not-a-valid-qr-token-material"}
    for _ in range(5):
        response = await client.post("/api/v1/attendance/check-in", json=payload, headers={"X-Device-Api-Key": "invalid"})
        assert response.status_code == 401
    assert await redis.get(f"ypgym:rate:scanner:{hash_token('test-gate')}") is None
    for index in range(60):
        path = "/api/v1/attendance/check-in" if index % 2 else "/api/v1/attendance/check-out"
        response = await client.post(path, json=payload, headers={"X-Device-Api-Key": "valid-test-key"})
        assert response.status_code == 400
    response = await client.post("/api/v1/attendance/check-out", json=payload, headers={"X-Device-Api-Key": "valid-test-key"})
    assert response.status_code == 429


async def test_validation_does_not_echo_credentials_or_invalid_input(client):
    payload = {"password": "PRIVATE-PASSWORD-MARKER", "token": "PRIVATE-TOKEN-MARKER"}
    result = await client.post("/api/v1/auth/login", json=payload)
    assert result.status_code == 422
    assert "PRIVATE" not in result.text
    assert all(set(item) == {"type", "loc", "msg"} for item in result.json()["error"]["details"])


async def test_redis_outage_returns_503_before_authentication(client):
    from app.main import app
    class OfflineRedis:
        async def eval(self, *args):
            raise ConnectionError("private-internal-detail")
    previous = app.dependency_overrides[get_redis_client]
    app.dependency_overrides[get_redis_client] = lambda: OfflineRedis()
    try:
        response = await client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "invalid"})
        assert response.status_code == 503
        assert "private-internal-detail" not in response.text
    finally:
        app.dependency_overrides[get_redis_client] = previous


@pytest.mark.parametrize("role, expected", [("member", 403), ("staff", 403), ("pt", 403), ("manager", 200), ("admin", 200)])
async def test_analytics_authorization_uses_persisted_role(client, storage, role, expected):
    sessions, _ = storage
    user = User(id=uuid4(), name="Role test", email=f"{role}@example.com", phone="123456789", role=role, password_hash="unused", is_email_verified=True)
    async with sessions() as session:
        session.add(user)
        await session.commit()
    # Deliberately lie in the signed role claim: database authorization must win.
    token, _ = create_access_token(user_id=user.id, role="admin", tier="vip")
    result = await client.get("/api/v1/admin/analytics/summary", headers={"Authorization": f"Bearer {token}"})
    assert result.status_code == expected
    if expected == 200:
        for params in (
            {"date_from": "2026-01-01T00:00:00"},
            {"date_from": "2026-02-01T00:00:00Z", "date_to": "2026-01-01T00:00:00Z"},
            {"date_from": "2020-01-01T00:00:00Z", "date_to": "2026-01-01T00:00:00Z"},
        ):
            assert (await client.get("/api/v1/admin/analytics/summary", params=params, headers={"Authorization": f"Bearer {token}"})).status_code == 422


async def test_missing_invalid_and_expired_jwt_rejected(client):
    settings = get_settings()
    expired = jwt.encode({"sub": str(uuid4()), "exp": datetime.now(UTC) - timedelta(seconds=1)}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    for headers in ({}, {"Authorization": "Bearer malformed"}, {"Authorization": f"Bearer {expired}"}):
        assert (await client.get("/api/v1/admin/analytics/summary", headers=headers)).status_code == 401


async def test_access_token_purpose_and_required_claims(client, storage):
    sessions, _ = storage
    settings = get_settings()
    user = User(id=uuid4(), name="Token test", email="tokens@example.com", phone="123456789", password_hash="unused", is_email_verified=True)
    async with sessions() as session:
        session.add(user)
        await session.commit()
    legacy = {"sub": str(user.id), "role": "member", "tier": "normal", "exp": datetime.now(UTC) + timedelta(minutes=1)}
    cases = [
        (legacy, 200),
        ({**legacy, "type": "access"}, 200),
        ({**legacy, "type": "attendance_qr", "jti": "test-qr"}, 401),
        ({key: value for key, value in legacy.items() if key != "exp"}, 401),
        ({key: value for key, value in legacy.items() if key != "role"}, 401),
        ({**legacy, "sub": "invalid-uuid"}, 401),
        ({**legacy, "exp": None}, 401),
    ]
    for payload, expected in cases:
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == expected
