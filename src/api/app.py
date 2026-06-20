"""`create_app()` factory for the M3 API skeleton.

Single entrypoint. Construct a fresh `FastAPI` instance per
call. The factory is pure: no module-level globals, no DB pool,
no implicit logger registration.

Launch contract:

    uvicorn src.api.app:create_app --factory

This script-safe construction is what enables the test client
to build a fresh app per test without touching process state.
"""
from __future__ import annotations

from fastapi import FastAPI

from src.api.errors import register_exception_handlers
from src.api.middleware.correlation import CorrelationIdMiddleware
from src.api.routers.health import router as health_router


def create_app() -> FastAPI:
    """Build and configure the V1 API skeleton."""
    app = FastAPI(
        title="sagewell-v1-skeleton",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    return app
