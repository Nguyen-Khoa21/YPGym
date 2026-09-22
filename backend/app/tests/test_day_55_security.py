import pytest
from redis.exceptions import RedisError

from app.core.rate_limit import RateLimitService
from app.core.exceptions import AppError, DependencyUnavailableError


class FakeRedis:
    def __init__(self, *, count: int = 0, fail: bool = False) -> None:
        self.count = count
        self.fail = fail
        self.expiry: tuple[str, int] | None = None

    async def eval(self, script: str, key_count: int, key: str, limit: int, seconds: int):
        if self.fail:
            raise RedisError("offline")
        self.count += 1
        self.expiry = (key, seconds)
        return self.count, 42


@pytest.mark.asyncio
async def test_sensitive_rate_limit_sets_window_and_rejects_over_limit() -> None:
    redis = FakeRedis()
    limiter = RateLimitService()
    await limiter.enforce(redis, key="login", limit=1, window_seconds=60)
    assert redis.expiry == ("login", 60)
    with pytest.raises(AppError) as exc_info:
        await limiter.enforce(redis, key="login", limit=1, window_seconds=60)
    assert exc_info.value.code == "RATE_LIMITED"
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_sensitive_rate_limit_fails_closed_when_redis_is_unavailable() -> None:
    with pytest.raises(DependencyUnavailableError) as exc_info:
        await RateLimitService().enforce(FakeRedis(fail=True), key="scanner", limit=60, window_seconds=60)
    assert exc_info.value.code == "RATE_LIMIT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_failure_logs_exclude_exception_values_and_untrusted_request_id(caplog):
    import httpx
    from fastapi import FastAPI
    from app.core.exceptions import register_exception_handlers
    from app.core.logging import add_request_logging

    app = FastAPI()
    register_exception_handlers(app)
    add_request_logging(app)

    @app.get("/failure")
    async def fail():
        raise RuntimeError("PRIVATE_SQL_PASSWORD_AND_TOKEN")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
        response = await client.get("/failure", headers={"x-request-id": "PRIVATE_REQUEST_ID"})
    assert response.status_code == 500
    assert "PRIVATE" not in response.text and "PRIVATE" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_uvicorn_does_not_log_query_tokens_or_reraised_exception_values(caplog):
    import logging
    from app.core.logging import configure_logging

    configure_logging()
    logging.getLogger("uvicorn.access").error("GET /verify-email?token=PRIVATE_QUERY")
    try:
        raise ValueError("PRIVATE_DATABASE_VALUE")
    except ValueError:
        logging.getLogger("uvicorn.error").exception("ASGI failure PRIVATE_MESSAGE")
    assert "PRIVATE" not in caplog.text
    assert "exception_type=ValueError" in caplog.text


@pytest.mark.asyncio
async def test_development_email_keeps_one_time_link_out_of_logs(tmp_path, caplog):
    from mailbox import Maildir
    from types import SimpleNamespace
    from app.services.auth_service import AuthService

    service = AuthService(None)
    service.settings = SimpleNamespace(
        ENVIRONMENT="development",
        EMAIL_DELIVERY_MODE="development",
        EMAIL_SENDER_NAME="YPGym Team",
        EMAIL_SENDER_ADDRESS="no-reply@example.com",
        FRONTEND_URL="http://localhost:5174",
        DEVELOPMENT_MAIL_DIR=str(tmp_path / "mail"),
    )
    await service._prepare_development_email("synthetic@example.com", "Password reset", "/reset-password", "PRIVATE_RESET_MATERIAL")
    outbox = Maildir(tmp_path / "mail", create=False)
    try:
        messages = list(outbox.values())
        assert len(messages) == 1
        assert "PRIVATE_RESET_MATERIAL" in messages[0].get_payload()
        assert messages[0]["To"] == "synthetic@example.com"
        assert "PRIVATE_RESET_MATERIAL" not in caplog.text
        service.settings.ENVIRONMENT = "test"
        await service._prepare_development_email("synthetic@example.com", "Password reset", "/reset-password", "NOT_WRITTEN")
        assert len(outbox) == 1
    finally:
        outbox.close()
