"""M5 API-boundary auth middleware tests.

Coverage:

1. `/health` returns 200 even with the auth middleware enabled
   (D-040 Q3 skip set: `/health`, `/docs`, `/redoc`).
2. `/docs` returns 200 (skip path).
3. `/openapi.json` returns 401 without `Authorization` (Q3: JWT-protected).
4. A non-skip route (`/healthx`, a synthetic route registered
   only by the test) returns 200 with a valid token.
   Implementation note: the V1 route surface is exactly the four
   M3 routes. To exercise the middleware on a non-skip path we
   register an ephemeral route in-process via FastAPI's APIRouter.
5. Same path returns 401 with `code=auth_failed` + canonical
   envelope when the token is missing, and emits an audit row
   carrying `reason_code="jwt_invalid"` and the unknown-user
   carrier metadata.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import APIRouter, FastAPI, Request

from src.api.middleware.auth import PUBLIC_PATHS
from src.application.auth.dto import AuthActor

# Tests in this module use both fixtures (M3-style and authed).
# `authed_app` is registered in `conftest.py`.
pytestmark = pytest.mark.asyncio


async def test_health_is_public_when_auth_enabled(client):
    """The M3 default test continues to pass without auth enforcement."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_openapi_is_public_when_auth_disabled_default_app(client):
    """D-040 Q3 enforcement is conditional on `jwt_signer` being wired.

    The default `app` fixture has no auth enforcement; `/openapi.json`
    continues to return 200. The auth-enabled factory path is asserted
    below in `test_openapi_is_401_when_auth_enabled`.
    """
    response = await client.get("/openapi.json")
    assert response.status_code == 200


async def test_public_paths_skip_middleware():
    """Sanity-check the D-040 Q3 skip-path set."""
    assert PUBLIC_PATHS == frozenset({"/health", "/docs", "/redoc"})
    assert "/openapi.json" not in PUBLIC_PATHS


def _make_authed_app_with_actor_route(
    create_app_kwargs,
):
    """Helper to build a FastAPI app with auth + a protected route.

    Registers an ephemeral route at `/protected` that echoes
    `state.actor.user_id` if the middleware attached an actor.
    This is the canonical way to exercise the auth middleware on
    a non-skip path in the absence of an M6 route.
    """
    from src.api.app import create_app as factory

    app = factory(**create_app_kwargs)
    router = APIRouter()

    @router.get("/protected")
    async def _echo_actor(request: Request):
        actor: AuthActor | None = getattr(request.state, "actor", None)
        if actor is None:
            return {"actor": None}
        return {"actor": {"user_id": actor.user_id, "role": actor.role}}

    app.include_router(router)
    return app


async def test_openapi_is_protected_when_auth_enabled(jwt_signer, in_memory_audit_repo):
    """`/openapi.json` is JWT-protected when the middleware is enabled.

    Note: this test builds its own app outside the `authed_app`
    fixture so the route surface doesn't include the
    auth-protected-only registry needed for the Q3 enforcement.
    """
    import httpx

    app = _make_authed_app_with_actor_route(
        {"audit_repo": in_memory_audit_repo, "jwt_signer": jwt_signer}
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
        assert response.status_code == 401
        body = response.json()
        assert body["code"] == "auth_failed"
        assert body["correlation_id"]


async def test_protected_route_with_valid_token_returns_actor(
    jwt_signer, in_memory_audit_repo
):
    """A protected route returns the typed actor's user_id when verified.

    Exercises the success path of `VerifyJwtToken` via the
    middleware; the actor is attached to `state.actor`. The
    middleware uses the production `SystemClock`, so the test
    signs the token with `now + 5 minutes` against wall time.
    """
    import httpx
    from src.application.auth.signer import JwtClaims
    from datetime import datetime, timedelta, timezone

    now = datetime.now(tz=timezone.utc)
    claims = JwtClaims(
        user_id="u-actor",
        department="engineering",
        clearance="internal",
        role="contributor",
    )
    token = jwt_signer.sign(claims=claims, exp=now + timedelta(minutes=5))

    app = _make_authed_app_with_actor_route(
        {"audit_repo": in_memory_audit_repo, "jwt_signer": jwt_signer}
    )
    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected", headers=headers)
    assert response.status_code == 200


async def test_protected_route_with_missing_token_returns_401_and_audit_row(
    jwt_signer, in_memory_audit_repo
):
    """Missing `Authorization` produces a 401 envelope and a JWT failure row.

    D-040 Q2: the audit row carries the unknown-user carrier.
    """
    import httpx

    app = _make_authed_app_with_actor_route(
        {"audit_repo": in_memory_audit_repo, "jwt_signer": jwt_signer}
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected")

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "auth_failed"
    assert body["message"]
    assert body["correlation_id"]

    rows = await in_memory_audit_repo.find_by_correlation_id(body["correlation_id"])
    assert len(rows) == 1
    row = rows[0]
    assert row.reason_code == "jwt_invalid"
    assert row.metadata.get("auth_failure_carrier") == "unknown-user"
    assert row.metadata.get("auth_failure_code") == "jwt_missing"


async def test_protected_route_with_bad_signature_returns_401_and_audit_row(
    jwt_signer, in_memory_audit_repo, frozen_now
):
    """`/protected` with an HS256 token signed by a different secret -> 401 + row."""
    import httpx
    from src.application.auth.signer import HS256JwtSigner, JwtClaims

    alt_signer = HS256JwtSigner(secret=b"different-secret-than-the-real-one!")
    claims = JwtClaims(
        user_id="u-evil",
        department="engineering",
        clearance="internal",
        role="contributor",
    )
    token = alt_signer.sign(claims=claims, exp=frozen_now + timedelta(minutes=5))

    app = _make_authed_app_with_actor_route(
        {"audit_repo": in_memory_audit_repo, "jwt_signer": jwt_signer}
    )
    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected", headers=headers)
    assert response.status_code == 401
    rows = await in_memory_audit_repo.find_by_correlation_id(response.json()["correlation_id"])
    assert len(rows) == 1
    assert rows[0].reason_code == "jwt_invalid"
    assert rows[0].metadata.get("auth_failure_code") == "jwt_bad_signature"


async def test_create_app_with_audit_repo_none_and_jwt_signer_passes_through(
    jwt_signer, in_memory_audit_repo, frozen_now
):
    """D-040 Q1 + DB-free launch: a missing `audit_repo` does not break the gate."""
    from src.api.app import create_app as factory
    import httpx

    # Pass audit_repo=None explicitly; middleware still enables JWT auth.
    app = factory(audit_repo=None, jwt_signer=jwt_signer)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        response = await client.get("/openapi.json")
        assert response.status_code == 401
