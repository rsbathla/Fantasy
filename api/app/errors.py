"""Error types + handlers producing ONE consistent error envelope.

Envelope (every error response, no exceptions):
    {
      "error": {"code": "<machine_code>", "message": "<human>", "details": [...]},
      "request_id": "<uuid>"
    }
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("bestball.api")


class AppError(Exception):
    """Base application error mapped to the standard envelope."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[List[Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or []


class NotFound(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class Conflict(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class Unauthorized(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ServiceUnavailable(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "service_unavailable"


def _envelope(request: Request, code: str, message: str, details: Optional[List[Any]] = None) -> dict:
    return {
        "error": {"code": code, "message": message, "details": details or []},
        "request_id": getattr(request.state, "request_id", None),
    }


def _json(request: Request, status_code: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=_envelope(request, code, message, details))


# ---- handlers ----------------------------------------------------------------

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _json(request, exc.status_code, exc.code, exc.message, exc.details)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # jsonable_encoder makes the raw pydantic errors JSON-safe (handles ValueError ctx etc.)
    details = jsonable_encoder(exc.errors())
    return _json(
        request,
        422,  # Unprocessable Content
        "validation_error",
        "Request validation failed.",
        details,
    )


_HTTP_CODE_MAP = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    503: "service_unavailable",
}


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_CODE_MAP.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "HTTP error."
    return _json(request, exc.status_code, code, message)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the full traceback server-side; NEVER leak internals to the client.
    log.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return _json(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "internal_error",
        "An internal error occurred.",
    )


def register_exception_handlers(app) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
