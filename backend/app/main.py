from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import add_request_logging, configure_logging
from app.core.security_headers import add_security_headers
from app.services.attendance_realtime_service import attendance_realtime_hub

settings = get_settings()
configure_logging()


def cors_origins() -> list[str]:
    configured = [settings.FRONTEND_URL, *settings.CORS_EXTRA_ORIGINS.split(",")]
    return list(dict.fromkeys(origin.strip().rstrip("/") for origin in configured if origin.strip()))

@asynccontextmanager
async def lifespan(_: FastAPI):
    await attendance_realtime_hub.start()
    try:
        yield
    finally:
        await attendance_realtime_hub.stop()


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
add_security_headers(app, environment=settings.ENVIRONMENT)
add_request_logging(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
