"""Correlation-Id ASGI middleware for the M3 API skeleton.

Reads the `X-Correlation-ID` request header. If absent, generates
a fresh UUID4. The id is attached to the response header.

M3 has no domain/projection coupling: this middleware only
echoes or generates the header. Future milestones (M4 audit, M6
LangGraph) will opt in to *reading* the correlation id from
`request.state.correlation_id` and acting on it.
"""
from __future__ import annotations

import uuid


_HEADER_NAME = "X-Correlation-ID"


def _resolve_correlation_id(header_value: str | None) -> str:
    """Return the supplied header value or generate a UUID4."""
    if header_value:
        return header_value
    return str(uuid.uuid4())


class CorrelationIdMiddleware:
    """Tiny pure-ASGI middleware that reads/sets the correlation header.

    Pure ASGI (no `BaseHTTPMiddleware`) keeps the middleware layer
    well-defined for the skeleton. Reads only `X-Correlation-ID`
    on the way in; sets the same header on the way out.
    """

    def __init__(self, app) -> None:
        self._app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        cid = _resolve_correlation_id(
            _extract_header(scope.get("headers") or [])
        )
        scope.setdefault("state", {})["correlation_id"] = cid

        async def send_with_correlation(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers.append((_HEADER_NAME.lower().encode("latin-1"), cid.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self._app(scope, receive, send_with_correlation)


def _extract_header(headers: list[tuple[bytes, bytes]]) -> str | None:
    """Pull the X-Correlation-ID header out of an ASGI headers list."""
    needle = _HEADER_NAME.lower().encode("latin-1")
    for name, value in headers:
        if name.lower() == needle:
            return value.decode("latin-1", errors="replace")
    return None
