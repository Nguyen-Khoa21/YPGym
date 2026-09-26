from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.auth_schema import LoginResponse


ProviderName = Literal["google", "facebook"]


class ProviderStatus(BaseModel):
    provider: ProviderName
    enabled: bool


class OAuthStartResponse(BaseModel):
    authorization_url: str


class OAuthExchangeRequest(BaseModel):
    code: str = Field(min_length=24, max_length=512)


class OAuthExchangeResponse(LoginResponse):
    pass


class IdentityItem(BaseModel):
    provider: ProviderName
    email: str | None
    email_verified: bool
    last_login_at: datetime | None


class IdentityListResponse(BaseModel):
    password_enabled: bool
    identities: list[IdentityItem]
