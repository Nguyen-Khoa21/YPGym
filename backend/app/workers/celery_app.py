from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ypgym",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)


@celery_app.task(name="app.workers.health_ping")
def health_ping() -> str:
    return "ok"
