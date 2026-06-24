"""M5: API-boundary JWT validation middleware.

Pure-ASGI (no `BaseHTTPMiddleware`), mirroring the M3
correlation-id middleware's pattern. The auth middleware
sits between the correlation middleware and the application
stack:

    correlation_id (read X-Correlation-ID, attach state.correlation_id)
        -> auth (read Authorization, call VerifyJwtToken, attach state.actor)
            -> exception handlers / routers

Behavior:

* `create_app()` without a `jwt_signer` keyword argument leaves
  the middleware in M3-style passthrough mode. The dev launch
  contract `uvicorn src.api.app:create_app --factory` boots
  without auth; tests and dev work on the four M3 routes
  unchanged. Per D-039/D-040 the auth gate fires only when a
  `VerifyJwtToken` is wired into `app.state.verify_jwt` at
  factory-time.

* `create_app(..., jwt_signer=...)` enables the middleware.
  `/health`, `/docs`, and `/redoc` skip the middleware. Every
  other path requires a `Bearer` token; missing / malformed /
  bad-signature / expired / generic-invalid tokens produce a
  401 envelope and a `RecordAuditEvent` row carrying
  `reason_code="jwt_invalid"` via the use case.

* Successful verification attaches the typed `AuthActor` to
  `request.state.actor` for downstream consumers (M6+).

`/openapi.json` is JWT-protected when the middleware is enabled
(D-040 Q3). With no middleware, `/openapi.json` continues to
return the M3 default 200.

Boundary:

- Imports only from the application layer (HS256 signer is
  interior; the middleware calls `VerifyJwtToken`).
- Does NOT import from `src/infrastructure/` or any DB driver.
"""
from __future__ import annotations

import json
import logging
from typing import Awaitable, Callable

from src.application.auth.errors import AuthFailure, JwtMalformed, JwtMissing
from src.application.auth.verify_jwt import VerifyJwtToken
from src.application.auth.dto import VerifyJwtTokenCommand


_logger = logging.getLogger("sagewell.api.middleware.auth")

# Skip-path set per D-040 Q3. `/openapi.json` is JWT-protected;
# only the dev UI and the liveness route skip.
PUBLIC_PATHS: frozenset[str] = frozenset({"/health", "/docs", "/redoc"})

_AUTH_FAILED_CODE = "auth_failed"


class JwtAuthMiddleware:
    """Pure-ASGI JWT validation middleware.

    Reads the `Authorization: Bearer ...` request header. On
    success, attaches the typed actor to `scope["state"]["actor"]`.
    On any failure, returns 401 with the canonical
    `{code, message, correlation_id}` envelope. Persists the
    failure row through the wired `VerifyJwtToken` use case.

    The middleware is a no-op when the host app's
    `app.state.verify_jwt` is not set. That keeps the M3 launch
    contract intact.
    """

    def __init__(self, app) -> None:
        self._app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in PUBLIC_PATHS:
            await self._app(scope, receive, send)
            return

        state = scope.setdefault("state", {})
        # The middleware is wired only when `verify_jwt` is
        # present on the host app's state. We resolve at runtime
        # via `scope["app"]` (Starlette injects the FastAPI
        # instance); `self._app` may be a wrapped inner app in
        # the middleware stack and is not the right lookup.
        fastapi_app = scope.get("app")
        verify_jwt: VerifyJwtToken | None = (
            getattr(fastapi_app.state, "verify_jwt", None)
            if fastapi_app is not None
            else None
        )
        if verify_jwt is None:
            # Legacy / dev / test launch: no auth enforcement.
            await self._app(scope, receive, send)
            return

        correlation_id = state.get("correlation_id", "")

        header = _extract_header(scope.get("headers") or [])
        if header is None:
            # No header at all. Always defer to the use case so the
            # audit-row write stays in one place. The use case
            # accepts an empty token and records the failure.
            await self._dispatch_failure(
                scope, receive, send,
                correlation_id=correlation_id,
                token="",
                verify_jwt=verify_jwt,
            )
            return

        if not header.lower().startswith("bearer "):
            await self._dispatch_failure(
                scope, receive, send,
                correlation_id=correlation_id,
                token="",
                verify_jwt=verify_jwt,
            )
            return

        token = header[len("bearer "):].strip()
        if not token:
            await self._dispatch_failure(
                scope, receive, send,
                correlation_id=correlation_id,
                token="",
                verify_jwt=verify_jwt,
            )
            return

        await self._dispatch_token(
            scope, receive, send,
            correlation_id=correlation_id,
            token=token,
            verify_jwt=verify_jwt,
        )

    async def _dispatch_token(
        self,
        scope,
        receive,
        send: Callable[[dict], Awaitable[None]],
        *,
        correlation_id: str,
        token: str,
        verify_jwt: "VerifyJwtToken",
    ) -> None:
        try:
            actor = await verify_jwt(
                VerifyJwtTokenCommand(
                    token=token, correlation_id=correlation_id
                )
            )
        except AuthFailure as exc:
            await self._reject(
                scope, receive, send,
                correlation_id=correlation_id,
                exc=exc,
            )
            return

        state = scope.setdefault("state", {})
        state["actor"] = actor
        await self._app(scope, receive, send)

    async def _dispatch_failure(
        self,
        scope,
        receive,
        send: Callable[[dict], Awaitable[None]],
        *,
        correlation_id: str,
        token: str,
        verify_jwt: "VerifyJwtToken",
    ) -> None:
        """Forward a missing/malformed `token` to `verify_jwt` so the audit row is written.

        The use case accepts an empty token and raises the typed
        failure; the middleware then translates that failure into
        the canonical 401 envelope. This keeps every failure-row
        write in the use case's path.
        """
        try:
            await verify_jwt(
                VerifyJwtTokenCommand(
                    token=token, correlation_id=correlation_id
                )
            )
        except AuthFailure as exc:
            await self._reject(
                scope, receive, send,
                correlation_id=correlation_id,
                exc=exc,
            )
            return
        # If verify_jwt did not raise, we are in a degenerate
        # state; surface the canonical 401.
        await self._reject(
            scope, receive, send,
            correlation_id=correlation_id,
            exc=AuthFailure("Authorization header missing"),
        )

    @staticmethod
    async def _reject(
        scope,
        receive,
        send: Callable[[dict], Awaitable[None]],
        *,
        correlation_id: str,
        exc: AuthFailure,
    ) -> None:
        """Emit a 401 envelope response and stop the chain."""
        body = {
            "code": _AUTH_FAILED_CODE,
            "message": exc.message,
            "correlation_id": correlation_id,
        }
        encoded = json.dumps(body).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(encoded)).encode("ascii")),
                    (
                        b"x-correlation-id",
                        correlation_id.encode("latin-1", errors="replace"),
                    ),
                ],
            }
        )
        await send({"type": "http.response.body", "body": encoded, "more_body": False})


def _extract_header(headers):
    """Pull the `Authorization` header from an ASGI headers list."""
    needle = b"authorization"
    for name, value in headers:
        if name.lower() == needle:
            try:
                return value.decode("latin-1")
            except UnicodeDecodeError:
                return None
    return None
