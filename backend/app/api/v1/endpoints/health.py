from fastapi import APIRouter
from sqlalchemy import text
from redis.exceptions import RedisError

from app.core.exceptions import DependencyUnavailableError
from app.db.redis import redis_client
from app.db.session import AsyncSessionLocal
from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "success",
        "message": "YPGym API is running",
        "version": "0.1.0",
        "payment_provider": "payos",
        "payment_configuration": "ready" if settings.PAYOS_ENABLED else "disabled",
    }


@router.get("/health/dependencies")
async def dependency_health_check() -> dict[str, str]:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise DependencyUnavailableError(
            code="DATABASE_UNAVAILABLE",
            message="PostgreSQL is not available.",
        ) from exc

    try:
        await redis_client.ping()
    except (RedisError, OSError) as exc:
        raise DependencyUnavailableError(
            code="REDIS_UNAVAILABLE",
            message="Redis is not available.",
        ) from exc

    return {
        "status": "success",
        "database": "ok",
        "redis": "ok",
    }
