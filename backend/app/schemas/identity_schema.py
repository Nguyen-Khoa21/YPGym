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


class PendingLinkRequest(BaseModel):
    code: str = Field(min_length=24, max_length=512)


class PendingLinkPasswordRequest(PendingLinkRequest):
    password: str = Field(min_length=1, max_length=128)


class PendingLinkEmailConfirmRequest(BaseModel):
    token: str = Field(min_length=24, max_length=512)


class PendingLinkStatus(BaseModel):
    provider: ProviderName
    masked_email: str
    password_confirmation_available: bool
    email_confirmation_available: bool
    expires_at: datetime


class PendingLinkEmailResponse(BaseModel):
    message: str


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
