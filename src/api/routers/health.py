"""`GET /health` route for the M3 API skeleton.

Returns 200 + `{ "status": "ok" }` unconditionally. Does NOT
touch any DB driver, repository, audit log, or session. The
endpoint is intentionally framework-only; future health
probes (DB ping, model warm-up) live in M14.
"""
from __future__ import annotations

from fastapi import APIRouter

from src.api.schemas.health import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
