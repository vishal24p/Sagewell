"""Pytest fixtures for the V1 API tests.

The `app` fixture invokes the same `create_app()` factory the
production launch contract uses, so coverage is faithful.

The `client` fixture builds an `httpx.AsyncClient` against the
app via `ASGITransport`. ASGI transport lets us exercise the
full ASGI stack (middleware + exception handlers) without a
real socket.

M5 adds fixtures for the auth-enabled factory path:
`authed_app` and `authed_client`.
"""
from __future__ import annotations

import pytest

import httpx

from src.api.app import create_app
from src.application.auth.signer import HS256JwtSigner
from src.application.audit_event.clock import Clock
from datetime import datetime, timedelta, timezone
from src.domain.ports.audit_logs import AuditLogRepository
from src.infrastructure.repositories.in_memory.audit_logs import (
    InMemoryAuditLogRepository,
)


@pytest.fixture
def app():
    """A fresh M3-style API instance per test (no auth middleware)."""
    return create_app()


@pytest.fixture
def client(app):
    """An `httpx.AsyncClient` bound to the ASGI transport."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


_SEED_SECRET = b"dev-secret-for-tests-with-32-byte-min-len!"


class _FrozenClock:
    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed


@pytest.fixture
def jwt_signer() -> HS256JwtSigner:
    return HS256JwtSigner(secret=_SEED_SECRET)


@pytest.fixture
def frozen_now() -> datetime:
    return datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def in_memory_audit_repo() -> AuditLogRepository:
    return InMemoryAuditLogRepository()


@pytest.fixture
def authed_app(jwt_signer, in_memory_audit_repo):
    """A factory-built API instance with the M5 auth middleware enabled.

    Uses the in-memory audit_log adapter (M2 parity) so the
    failure-row assertions are observable end-to-end through
    the middleware.
    """
    return create_app(audit_repo=in_memory_audit_repo, jwt_signer=jwt_signer)


@pytest.fixture
def authed_client(authed_app, in_memory_audit_repo):
    """An ASGI client bound to the auth-enabled API and audit repo fixtures.

    Returns the tuple `(client, audit_repo)` so tests can read
    the audit rows directly.
    """
    transport = httpx.ASGITransport(app=authed_app)
    return (
        httpx.AsyncClient(transport=transport, base_url="http://test"),
        in_memory_audit_repo,
    )
