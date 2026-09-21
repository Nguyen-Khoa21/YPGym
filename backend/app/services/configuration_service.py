from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ResourceNotFoundError
from app.models.user import User
from app.repositories.operations_repository import AuditRepository, ConfigurationRepository
from app.schemas.operations_schema import ConfigurationItem


@dataclass(frozen=True)
class ConfigurationRule:
    minimum: int
    maximum: int
    default: int


CONFIGURATION_RULES = {
    "gym_capacity": ConfigurationRule(1, 5000, 150),
    "qr_token_ttl_seconds": ConfigurationRule(15, 300, 60),
    "attendance_timeout_minutes": ConfigurationRule(15, 1440, 180),
    "duplicate_scan_window_seconds": ConfigurationRule(1, 300, 30),
    "class_cancellation_window_hours": ConfigurationRule(0, 168, 12),
    "class_reminder_lead_minutes": ConfigurationRule(5, 1440, 120),
    "waitlist_size": ConfigurationRule(0, 100, 10),
}


def validate_configuration_value(key: str, value: int) -> int:
    rule = CONFIGURATION_RULES.get(key)
    if not rule:
        raise ResourceNotFoundError("Configuration key was not found.")
    if not rule.minimum <= value <= rule.maximum:
        raise AppError(
            "CONFIGURATION_VALUE_OUT_OF_RANGE",
            f"{key} must be between {rule.minimum} and {rule.maximum}.",
            422,
            {"minimum": rule.minimum, "maximum": rule.maximum},
        )
    return value


class ConfigurationService:
    CACHE_PREFIX = "ypgym:config:"

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.configurations = ConfigurationRepository(session)
        self.audit = AuditRepository(session)

    async def get_int(self, key: str) -> int:
        if key not in CONFIGURATION_RULES:
            raise ResourceNotFoundError("Configuration key was not found.")
        cache_key = f"{self.CACHE_PREFIX}{key}"
        try:
            cached = await self.redis.get(cache_key)
            if cached is not None:
                return validate_configuration_value(key, int(cached))
        except (RedisError, ValueError):
            pass
        record = await self.configurations.get(key)
        value = validate_configuration_value(
            key,
            int(record.value) if record else CONFIGURATION_RULES[key].default,
        )
        try:
            await self.redis.set(cache_key, str(value), ex=300)
        except RedisError:
            pass
        return value

    async def list_items(self) -> list[ConfigurationItem]:
        records = await self.configurations.list_keys(tuple(CONFIGURATION_RULES))
        by_key = {item.key: item for item in records}
        return [
            ConfigurationItem(
                key=key,
                value=validate_configuration_value(key, int(by_key[key].value)),
                description=by_key[key].description,
                updated_at=by_key[key].updated_at,
            )
            for key in sorted(by_key)
        ]

    async def update(self, *, key: str, value: int, actor: User) -> ConfigurationItem:
        value = validate_configuration_value(key, value)
        record = await self.configurations.get(key)
        if not record:
            raise ResourceNotFoundError("Configuration key was not found.")
        before = int(record.value)
        record.value = str(value)
        await self.audit.create(
            actor_user_id=actor.id,
            action="configuration.updated",
            entity_type="system_configuration",
            entity_id=str(record.id),
            reason="Operational configuration update",
            outcome="updated",
            summary=f"Configuration {key} changed from {before} to {value}.",
            before_data={"key": key, "value": before},
            after_data={"key": key, "value": value},
        )
        await self.session.commit()
        try:
            await self.redis.delete(f"{self.CACHE_PREFIX}{key}")
        except RedisError:
            pass
        await self.session.refresh(record)
        return ConfigurationItem(
            key=record.key,
            value=value,
            description=record.description,
            updated_at=record.updated_at,
        )
