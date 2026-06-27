"""M3: OpenAPI route surface and built-in docs UIs."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_openapi_json_returns_document(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    document = response.json()
    assert "/health" in document["paths"]
    assert "HealthResponse" in document["components"]["schemas"]


@pytest.mark.asyncio
async def test_docs_and_redoc_load(client):
    for path in ("/docs", "/redoc"):
        response = await client.get(path)
        assert response.status_code == 200, path


@pytest.mark.asyncio
async def test_route_surface_is_m9(client):
    """M9 widens the M3 route surface with /v1/query.

    The launch contract stays DB-free unless the runtime
    runner wires the M9 orchestrator; the surface that
    OpenAPI documents is `/health` plus `/v1/query`. The
    M3 strict-route guard is preserved at M9 because both
    routes are JWT-aware: `/health` is the public path,
    `/v1/query` requires an authenticated actor.
    """
    openapi = await client.get("/openapi.json")
    paths = set(openapi.json()["paths"].keys())
    assert paths == {"/health", "/v1/query"}
