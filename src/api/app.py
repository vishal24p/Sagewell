"""`create_app()` factory for the M3 API skeleton.

Single entrypoint. Construct a fresh `FastAPI` instance per
call. The factory is pure: no module-level globals, no DB pool,
no implicit logger registration.

Launch contract:

    uvicorn src.api.app:create_app --factory

This script-safe construction is what enables the test client
to build a fresh app per test without touching process state.

M4 dependency-injection seam (per D-031, D-035):

    create_app(*, audit_repo: Optional[AuditLogRepository] = None)
        -> FastAPI

The factory does NOT construct a pool. `__main__.py` owns
pool construction and passes a fully-built repository
through this seam. The factory remains DB-free at import
time and at runtime when `audit_repo is None`.

No middleware or route consumes `audit_repo` at M4 request
time. The seam is the only thing M4 ships; future milestones
(M5+) will plug request-time audit-write behaviour onto it.
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI

from src.api.errors import register_exception_handlers
from src.api.middleware.correlation import CorrelationIdMiddleware
from src.api.routers.health import router as health_router


def create_app(
    *,
    audit_repo: Optional["AuditLogRepository"] = None,
) -> FastAPI:
    """Build and configure the V1 API skeleton.

    Args:
        audit_repo: Optional `AuditLogRepository` Protocol from
            `src.domain.ports.audit_logs`. When supplied it is
            made reachable via `app.state.audit_repo`. M4 does
            not consume it; the seam exists for M5+ to plug in
            without needing to modify `create_app`.
    """
    app = FastAPI(
        title="sagewell-v1-skeleton",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    if audit_repo is not None:
        app.state.audit_repo = audit_repo
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    return app

