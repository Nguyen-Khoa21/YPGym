from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.exceptions import AppError, DependencyUnavailableError


class RateLimitService:
    """Small Redis-backed fixed-window limiter for sensitive endpoints."""

    # Count and expiry must be one operation, including recovery of old keys
    # left without an expiry by the previous two-command implementation.
    SCRIPT = """
    local count = tonumber(redis.call('GET', KEYS[1]) or '0')
    if count < tonumber(ARGV[1]) then
        count = redis.call('INCR', KEYS[1])
    else
        count = count + 1
    end
    if redis.call('TTL', KEYS[1]) < 0 then
        redis.call('EXPIRE', KEYS[1], ARGV[2])
    end
    return {count, redis.call('TTL', KEYS[1])}
    """

    async def enforce(self, redis: Redis, *, key: str, limit: int, window_seconds: int) -> None:
        try:
            count, ttl = await redis.eval(self.SCRIPT, 1, key, limit, window_seconds)
            if count > limit:
                raise AppError(
                    "RATE_LIMITED",
                    "Too many requests. Please try again later.",
                    429,
                    {"retry_after_seconds": max(int(ttl), 1)},
                )
        except AppError:
            raise
        except RedisError as exc:
            raise DependencyUnavailableError(
                "RATE_LIMIT_UNAVAILABLE",
                "This request cannot be processed while abuse protection is unavailable.",
            ) from exc


rate_limits = RateLimitService()
