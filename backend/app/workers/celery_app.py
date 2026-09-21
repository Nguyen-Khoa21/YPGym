import asyncio
from collections.abc import Awaitable, Callable

from celery import Celery
from celery.schedules import crontab
from redis.asyncio import Redis

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, engine
from app.services.attendance_service import AttendanceService
from app.services.configuration_service import ConfigurationService
from app.services.lifecycle_service import MembershipLifecycleService
from app.services.notification_service import NotificationService

settings = get_settings()

celery_app = Celery(
    "ypgym",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.beat_schedule = {
    "membership-lifecycle-hourly": {
        "task": "app.workers.synchronize_memberships",
        "schedule": crontab(minute=5),
    },
    "expiry-reminders-daily": {
        "task": "app.workers.send_expiry_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
    "attendance-timeouts-five-minutes": {
        "task": "app.workers.close_timed_out_attendance",
        "schedule": 300.0,
    },
    "class-reminders-minute": {
        "task": "app.workers.send_class_reminders",
        "schedule": 60.0,
    },
}


@celery_app.task(name="app.workers.health_ping")
def health_ping() -> str:
    return "ok"


async def _run_with_disposal(operation: Callable[[], Awaitable[int]]) -> int:
    try:
        return await operation()
    finally:
        # Celery tasks are synchronous entry points and each asyncio.run call
        # owns a new event loop. Never retain asyncpg pooled connections that
        # were created by the loop being closed.
        await engine.dispose()


def _run_async_task(operation: Callable[[], Awaitable[int]]) -> int:
    return asyncio.run(_run_with_disposal(operation))


async def _synchronize_memberships() -> int:
    async with AsyncSessionLocal() as session:
        return await MembershipLifecycleService(session).synchronize_membership_statuses()


@celery_app.task(name="app.workers.synchronize_memberships")
def synchronize_memberships() -> int:
    return _run_async_task(_synchronize_memberships)


async def _send_expiry_reminders() -> int:
    async with AsyncSessionLocal() as session:
        return await NotificationService(session).send_expiry_reminders()


@celery_app.task(name="app.workers.send_expiry_reminders")
def send_expiry_reminders() -> int:
    return _run_async_task(_send_expiry_reminders)


async def _send_class_reminders() -> int:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        async with AsyncSessionLocal() as session:
            lead_minutes = await ConfigurationService(session, redis).get_int("class_reminder_lead_minutes")
            return await NotificationService(session).send_class_reminders(lead_minutes=lead_minutes)
    finally:
        await redis.aclose()


@celery_app.task(name="app.workers.send_class_reminders")
def send_class_reminders() -> int:
    return _run_async_task(_send_class_reminders)


async def _close_timed_out_attendance() -> int:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        async with AsyncSessionLocal() as session:
            return await AttendanceService(session, redis).close_timed_out_sessions()
    finally:
        await redis.aclose()


@celery_app.task(name="app.workers.close_timed_out_attendance")
def close_timed_out_attendance() -> int:
    return _run_async_task(_close_timed_out_attendance)
