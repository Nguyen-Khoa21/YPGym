import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class AuthenticationError(AppError):
    def __init__(
        self,
        message: str = "Authentication is required.",
        details: Any = None,
    ) -> None:
        super().__init__(
            code="AUTHENTICATION_REQUIRED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class PermissionDeniedError(AppError):
    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        details: Any = None,
    ) -> None:
        super().__init__(
            code="PERMISSION_DENIED",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ResourceNotFoundError(AppError):
    def __init__(
        self,
        message: str = "The requested resource was not found.",
        details: Any = None,
    ) -> None:
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(AppError):
    def __init__(
        self,
        message: str = "The request conflicts with the current resource state.",
        details: Any = None,
    ) -> None:
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class DependencyUnavailableError(AppError):
    def __init__(
        self,
        code: str,
        message: str,
        details: Any = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


def error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_payload(exc.code, exc.message, exc.details)),
    )


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    error_codes = {
        status.HTTP_401_UNAUTHORIZED: "AUTHENTICATION_REQUIRED",
        status.HTTP_403_FORBIDDEN: "PERMISSION_DENIED",
        status.HTTP_404_NOT_FOUND: "RESOURCE_NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_payload(
            code=error_codes.get(exc.status_code, "HTTP_ERROR"),
            message=str(exc.detail),
            details=None,
        )),
    )


async def validation_error_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_payload(
            code="VALIDATION_ERROR",
            message="The request could not be validated.",
            details=exc.errors(),
        )),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_api_exception method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred.",
            details=None,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
