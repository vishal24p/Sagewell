"""M3: correlation-id middleware behavior."""
from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_supplied_correlation_id_is_echoed(client):
    headers = {"X-Correlation-ID": "client-supplied-value"}
    response = await client.get("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "client-supplied-value"


@pytest.mark.asyncio
async def test_missing_correlation_id_generates_uuid4(client):
    response = await client.get("/health")
    cid = response.headers.get("X-Correlation-ID")
    assert cid is not None
    uuid.UUID(cid, version=4)


@pytest.mark.asyncio
async def test_correlation_id_is_stable_across_requests(client):
    # Two independent requests with the same correlation id must
    # both echo it back.
    headers = {"X-Correlation-ID": "stable-id"}
    responses = [await client.get("/health", headers=headers) for _ in range(2)]
    assert all(r.headers.get("X-Correlation-ID") == "stable-id" for r in responses)
