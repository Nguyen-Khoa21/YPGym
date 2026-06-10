import logging
import sys
import time
import uuid

from fastapi import FastAPI, Request

request_logger = logging.getLogger("app.request")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started_at) * 1000
        request_logger.exception(
            "request_failed method=%s path=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            duration_ms,
            request_id,
        )
        raise

    duration_ms = (time.perf_counter() - started_at) * 1000
    response.headers["x-request-id"] = request_id
    request_logger.info(
        "request_completed method=%s path=%s status_code=%s duration_ms=%.2f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


def add_request_logging(app: FastAPI) -> None:
    app.middleware("http")(request_logging_middleware)
