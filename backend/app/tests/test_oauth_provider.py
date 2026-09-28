from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import SecretStr
from pydantic import ValidationError

from app.services import oauth_service
from app.core.config import Settings


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self.payload

    def raise_for_status(self) -> None:
        return None


class FakeClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        return None

    async def post(self, *_args, **_kwargs) -> FakeResponse:
        return FakeResponse({"id_token": "id-token", "access_token": "access-token"})

    async def get(self, *_args, **_kwargs) -> FakeResponse:
        return FakeResponse({"keys": [{"kid": "key-id"}]})


class FakeRedis:
    async def get(self, _key: str):
        return None

    async def set(self, *_args, **_kwargs) -> None:
        return None

    async def delete(self, _key: str) -> None:
        return None


@pytest.mark.asyncio
async def test_google_validates_at_hash_with_transient_access_token(monkeypatch):
    captured: dict = {}
    settings = SimpleNamespace(
        GOOGLE_OAUTH_WEB_CLIENT_ID="client-id",
        GOOGLE_OAUTH_WEB_CLIENT_SECRET=SecretStr("client-secret"),
    )

    monkeypatch.setattr(oauth_service.httpx, "AsyncClient", lambda **_kwargs: FakeClient())
    monkeypatch.setattr(oauth_service.jwt, "get_unverified_header", lambda _token: {"kid": "key-id"})
    monkeypatch.setattr(oauth_service.jwk, "construct", lambda _key: SimpleNamespace(to_pem=lambda: b"public-key"))

    def decode(*_args, **kwargs):
        captured.update(kwargs)
        return {
            "iss": "https://accounts.google.com",
            "sub": "google-subject",
            "nonce": "expected-nonce",
            "iat": int(datetime.now(UTC).timestamp()),
            "email": "member@example.com",
            "email_verified": True,
            "name": "Member",
        }

    monkeypatch.setattr(oauth_service.jwt, "decode", decode)

    profile = await oauth_service.OAuthProviderClient(settings, FakeRedis())._google(
        code="provider-code",
        redirect_uri="http://localhost:8001/api/v1/auth/oauth/google/callback",
        verifier="verifier",
        nonce="expected-nonce",
    )

    assert captured["access_token"] == "access-token"
    assert profile.subject == "google-subject"


def test_oauth_configuration_requires_pairs_https_and_exact_callback():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, GOOGLE_OAUTH_WEB_CLIENT_ID="id", GOOGLE_OAUTH_WEB_CLIENT_SECRET="")
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            FRONTEND_URL="http://example.com",
            OAUTH_CALLBACK_BASE_URL="http://localhost:8001/api/v1",
        )
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        FRONTEND_URL="https://app.example.com",
        MOBILE_WEB_URL="https://mobile.example.com",
        OAUTH_CALLBACK_BASE_URL="https://api.example.com/api/v1/",
        GOOGLE_OAUTH_WEB_CLIENT_ID="client-id",
        GOOGLE_OAUTH_WEB_CLIENT_SECRET="client-secret",
        FACEBOOK_APP_ID="app-id",
        FACEBOOK_APP_SECRET="app-secret",
    )
    service = oauth_service.OAuthService(None, FakeRedis(), settings=settings)
    assert service._callback_uri("google") == "https://api.example.com/api/v1/auth/oauth/google/callback"
    assert service._return_url("mobile", provider="google", code="one-time") == "ypgym://oauth/callback?provider=google&code=one-time"
    assert service._return_url("mobile_web", provider="google", code="one-time") == "https://mobile.example.com/oauth/callback?provider=google&code=one-time"
