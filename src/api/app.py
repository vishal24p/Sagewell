"""`create_app()` factory for the M3 API skeleton + M5 auth seam.

Single entrypoint. Construct a fresh `FastAPI` instance per
call. The factory is pure: no module-level globals, no DB pool,
no implicit logger registration.

Launch contract:

    uvicorn src.api.app:create_app --factory

This script-safe construction is what enables the test client
to build a fresh app per test without touching process state.

M4 dependency-injection seam (D-031, D-035):

    create_app(*, audit_repo: Optional[AuditLogRepository] = None)
        -> FastAPI

The factory does NOT construct a pool. `__main__.py` owns
pool construction and passes a fully-built repository
through this seam. The factory remains DB-free at import
time and at runtime when `audit_repo is None`.

M5 dependency-injection seams (D-038, D-039, D-040):

    create_app(
        *,
        audit_repo: Optional[AuditLogRepository] = None,
        jwt_signer: Optional[JwtSigner] = None,
    ) -> FastAPI

When `jwt_signer` is provided, `create_app()` constructs a
`VerifyJwtToken` use case bound to that signer and (when
non-None) the `audit_repo`. The auth middleware mounts and
runs on every request that is not in the public skip set.
When `jwt_signer is None` the middleware mounts as a no-op;
the API still boots and `/openapi.json` continues to return
200, preserving the M3 launch contract.
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI

from src.api.errors import register_exception_handlers
from src.api.middleware.auth import JwtAuthMiddleware
from src.api.middleware.correlation import CorrelationIdMiddleware
from src.api.protocols import RunQueryFn
from src.api.routers.health import router as health_router
from src.api.routers.query import router as query_router


def create_app(
    *,
    audit_repo: Optional["AuditLogRepository"] = None,
    jwt_signer: Optional["JwtSigner"] = None,
    run_query: Optional["RunQueryFn"] = None,
    regex_guard: Optional["RegexGuard"] = None,
) -> FastAPI:
    """Build and configure the V1 API.

    Args:
        audit_repo: optional `AuditLogRepository` Protocol from
            `src.domain.ports.audit_logs`. When supplied it is
            made reachable via `app.state.audit_repo` and is
            bound to the JWT-failure audit-row writer
            (M5 `VerifyJwtToken` use case).
        jwt_signer: optional `JwtSigner` Protocol from
            `src.application.auth.signer`. When supplied the
            API mounts the auth middleware. When None the
            middleware is a no-op.
    """
    from src.application.auth.signer import JwtSigner  # noqa: F401 - type-check helper

    app = FastAPI(
        title="sagewell-v1-skeleton",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    if audit_repo is not None:
        app.state.audit_repo = audit_repo

    if run_query is not None:
        app.state.run_query = run_query

    if regex_guard is not None:
        app.state.regex_guard = regex_guard

    if jwt_signer is not None:
        from src.application.auth.verify_jwt import VerifyJwtToken
        from src.application.audit_event.clock import SystemClock

        app.state.verify_jwt = VerifyJwtToken(
            signer=jwt_signer,
            audit_repo=audit_repo,
            clock=SystemClock(),
        )

    # Middleware order: the LAST `add_middleware` call wraps the
    # INNER-most layer; the FIRST is the OUTER-most one. We want
    # the auth middleware to see `state.correlation_id` (so the
    # canonical 401 envelope can carry the request's correlation
    # id). Adding auth LAST and correlation FIRST places
    # CorrelationIdMiddleware on the outer edge; every request
    # fills `correlation_id` BEFORE auth runs.
    app.add_middleware(JwtAuthMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(query_router)
    return app
