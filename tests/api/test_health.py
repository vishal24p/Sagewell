"""M3: `GET /health` liveness."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_response_model_contract(client):
    response = await client.get("/health")
    body = response.json()
    assert set(body.keys()) == {"status"}
    assert body["status"] == "ok"
