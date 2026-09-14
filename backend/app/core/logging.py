import logging
import sys
import time
import uuid

from fastapi import FastAPI, Request

request_logger = logging.getLogger("app.request")


class ServerExceptionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info:
            record.msg = "ASGI failure exception_type=%s"
            record.args = (record.exc_info[0].__name__,)
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


def configure_logging() -> None:
    # Uvicorn's access logger includes query strings (including verification links).
    # The middleware below records the request path and status without those values.
    logging.getLogger("uvicorn.access").disabled = True
    # Starlette re-raises handled exceptions to Uvicorn after sending the 500.
    logging.getLogger("uvicorn.error").addFilter(ServerExceptionFilter())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def request_logging_middleware(request: Request, call_next):
    try:
        request_id = str(uuid.UUID(request.headers.get("x-request-id", "")))
    except ValueError:
        request_id = str(uuid.uuid4())
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = (time.perf_counter() - started_at) * 1000
        request_logger.error(
            "request_failed method=%s path=%s duration_ms=%.2f request_id=%s exception_type=%s",
            request.method,
            request.url.path,
            duration_ms,
            request_id,
            type(exc).__name__,
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
