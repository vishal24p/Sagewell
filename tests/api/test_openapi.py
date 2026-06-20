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
async def test_route_surface_is_m3_strict(client):
    """M3 must expose only the four documented paths."""
    openapi = await client.get("/openapi.json")
    paths = set(openapi.json()["paths"].keys())
    assert paths == {"/health"}
