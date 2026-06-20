"""Error translation layer for the M3 API skeleton.

Two exception handlers in this turn:

* `RequestValidationError` -> 422 with the canonical error
  envelope (FastAPI's default for validation, only the body is
  rewrapped so the API returns the same envelope shape across
  every error class).

* A catch-all HTTP middleware that maps any uncaught exception
  to 500 with the canonical error envelope. Starlette's
  `ServerErrorMiddleware` re-raises by design even when a
  handler is registered, so we install a thin HTTP middleware
  that produces the 500 response and stashes the result on
  `request.state`. Starlette then passes the same response on
  through without the re-raise interfering with the test or
  client.

Domain-error mappings (`PersistenceError`, `ResourceNotFound`,
`DomainError`) are deferred to M4 where they naturally belong.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.errors.schemas import ErrorResponse
from src.api.middleware.correlation import _resolve_correlation_id


_logger = logging.getLogger("sagewell.api.errors")


def _correlation_id_for(request: Request) -> str:
    """Return the correlation id already on `request.state`, generated if absent."""
    cid = getattr(request.state, "correlation_id", None)
    if cid:
        return cid
    return _resolve_correlation_id(request.headers.get("X-Correlation-ID"))


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Map a Pydantic / FastAPI validation error to 422 + envelope."""
    cid = _correlation_id_for(request)
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            code="validation_error",
            message="Request validation failed.",
            correlation_id=cid,
        ).model_dump(),
        headers={"X-Correlation-ID": cid},
    )


def build_error_envelope_middleware():
    """Return an HTTP middleware that converts uncaught exceptions to 500 + envelope.

    The middleware swallows the exception, logs only the three
    keys mandated by decision D-027, and produces a JSON response
    that starlette will write before the outer ServerErrorMiddleware
    re-raises. The re-raise is harmless when the response has already
    been sent (httpx ASGITransport still surfaces a 500 response).
    """

    class _ErrorEnvelopeMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            try:
                return await call_next(request)
            except Exception as exc:  # noqa: BLE001 - intentional catch-all
                cid = _correlation_id_for(request)
                _logger.error(
                    "api.unhandled_exception",
                    extra={
                        "correlation_id": cid,
                        "exception_type": type(exc).__name__,
                        "exc_message": str(exc),
                    },
                )
                response = JSONResponse(
                    status_code=500,
                    content=ErrorResponse(
                        code="internal_error",
                        message="An unexpected error occurred.",
                        correlation_id=cid,
                    ).model_dump(),
                    headers={"X-Correlation-ID": cid},
                )
                return response

    return _ErrorEnvelopeMiddleware


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the error handlers to the given FastAPI app."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_middleware(build_error_envelope_middleware())
