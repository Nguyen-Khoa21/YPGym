import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security_headers import CONTENT_SECURITY_POLICY, add_security_headers


def production_settings(**overrides) -> dict:
    return {
        "_env_file": None,
        "ENVIRONMENT": "production",
        "FRONTEND_URL": "https://app.example.com",
        "MOBILE_WEB_URL": "https://mobile.example.com",
        "OAUTH_CALLBACK_BASE_URL": "https://api.example.com/api/v1",
        **overrides,
    }


def test_production_rejects_default_or_short_signing_and_device_secrets() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(
            **production_settings(
                JWT_SECRET_KEY="change-this-secret-in-production",
                IOT_DEVICE_API_KEY="local-iot-key",
            )
        )
    private_short_secret = "PRIVATE_SHORT_JWT"
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY") as exc_info:
        Settings(
            **production_settings(
                JWT_SECRET_KEY=private_short_secret,
                IOT_DEVICE_API_KEY="production-iot-device-key-32-characters",
            )
        )
    assert private_short_secret not in str(exc_info.value)
    with pytest.raises(ValidationError, match="IOT_DEVICE_API_KEY"):
        Settings(
            **production_settings(
                JWT_SECRET_KEY="production-jwt-secret-with-at-least-32-characters",
                IOT_DEVICE_API_KEY="local-iot-key",
            )
        )

    settings = Settings(
        **production_settings(
            JWT_SECRET_KEY="production-jwt-secret-with-at-least-32-characters",
            IOT_DEVICE_API_KEY="production-iot-device-key-32-characters",
        )
    )
    assert settings.ENVIRONMENT == "production"


def build_app(environment: str) -> FastAPI:
    app = FastAPI()
    add_security_headers(app, environment=environment)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


@pytest.mark.asyncio
async def test_security_headers_cover_http_responses_without_local_hsts() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=build_app("development")),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.headers["content-security-policy"] == CONTENT_SECURITY_POLICY
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    assert "strict-transport-security" not in response.headers


@pytest.mark.asyncio
async def test_hsts_is_enabled_only_for_https_production_requests() -> None:
    app = build_app("production")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert "strict-transport-security" not in (await client.get("/health")).headers
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get("/health")
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
