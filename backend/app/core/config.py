from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "YPGym API"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:5174"
    MOBILE_APP_URL: str = "ypgym://"
    GYM_TIMEZONE: str = "Asia/Ho_Chi_Minh"
    CORS_EXTRA_ORIGINS: str = ""
    DATABASE_URL: str = "postgresql+asyncpg://ypgym:ypgym_dev_password@localhost:5433/ypgym"
    REDIS_URL: str = "redis://localhost:6380/0"
    JWT_SECRET_KEY: str = "change-this-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    EMAIL_DELIVERY_MODE: Literal["development", "smtp"] = "development"
    EMAIL_SENDER_NAME: str = "YPGym Team"
    EMAIL_SENDER_ADDRESS: EmailStr = "no-reply@example.com"
    SMTP_HOST: str = ""
    SMTP_PORT: int = Field(default=587, ge=1, le=65535)
    SMTP_TLS_MODE: Literal["starttls", "ssl", "none"] = "starttls"
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: SecretStr = SecretStr("")
    SMTP_TIMEOUT_SECONDS: int = Field(default=10, ge=1, le=60)
    EMAIL_MAX_DELIVERY_ATTEMPTS: int = Field(default=5, ge=1, le=20)
    EMAIL_RETRY_DELAY_SECONDS: int = Field(default=300, ge=1, le=86400)
    EMAIL_DELIVERY_BATCH_SIZE: int = Field(default=25, ge=1, le=100)
    QR_TOKEN_TTL_SECONDS: int = 60
    ATTENDANCE_TIMEOUT_MINUTES: int = 180
    GYM_CAPACITY: int = 150
    IOT_DEVICE_API_KEY: str = "local-iot-key"
    DEVELOPMENT_SEED_PASSWORD: str = "YPGymDemo123!"
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60
    DEVELOPMENT_MAIL_DIR: str = "storage/mail"
    INVOICE_STORAGE_DIR: str = "storage/invoices"

    @field_validator("GYM_TIMEZONE")
    @classmethod
    def validate_gym_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("GYM_TIMEZONE must be a valid IANA timezone.") from exc
        return value

    @field_validator("EMAIL_SENDER_NAME", "EMAIL_SENDER_ADDRESS", "SMTP_HOST", "SMTP_USERNAME")
    @classmethod
    def reject_email_header_injection(cls, value: str) -> str:
        if "\r" in value or "\n" in value:
            raise ValueError("Email and SMTP settings cannot contain line breaks.")
        return value.strip()

    @model_validator(mode="after")
    def validate_smtp_configuration(self) -> "Settings":
        if self.EMAIL_DELIVERY_MODE != "smtp":
            return self
        if not self.SMTP_HOST:
            raise ValueError("SMTP_HOST is required when EMAIL_DELIVERY_MODE is smtp.")
        if not self.EMAIL_SENDER_ADDRESS:
            raise ValueError("EMAIL_SENDER_ADDRESS is required when EMAIL_DELIVERY_MODE is smtp.")
        password_configured = bool(self.SMTP_PASSWORD.get_secret_value())
        if bool(self.SMTP_USERNAME) != password_configured:
            raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be configured together.")
        if self.SMTP_USERNAME and self.SMTP_TLS_MODE == "none":
            raise ValueError("SMTP authentication requires TLS.")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
