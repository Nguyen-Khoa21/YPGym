from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator
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
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
