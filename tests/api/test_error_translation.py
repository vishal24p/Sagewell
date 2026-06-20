"""M3: error envelope translation."""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI

import httpx

from src.api.errors import register_exception_handlers
from src.api.middleware.correlation import CorrelationIdMiddleware


@pytest.mark.asyncio
async def test_unhandled_exception_returns_envelope():
    """Any uncaught exception returns the canonical envelope with 500."""

    def _raise_app() -> FastAPI:
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/boom")
        def boom():
            raise RuntimeError("boom-test")

        return app

    app = _raise_app()
    register_exception_handlers(app)
    transport = httpx.ASGITransport(app=app)

    headers = {"X-Correlation-ID": "cid-abc-123"}
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/boom", headers=headers)

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error"
    assert body["correlation_id"] == "cid-abc-123"
    assert body["message"]


@pytest.mark.asyncio
async def test_correlation_id_generation_when_missing(client):
    """Generate a UUID4 when no correlation id is supplied."""
    response = await client.get("/health")
    cid = response.headers.get("X-Correlation-ID")
    assert cid is not None
    assert cid != ""
    parsed = uuid.UUID(cid, version=4)
    assert str(parsed) == cid
