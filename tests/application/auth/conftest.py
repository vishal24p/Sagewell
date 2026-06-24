"""Test fixtures for the M5 auth package.

`frozen_now`: deterministic datetime (M5 + M4 conventions).
`seed_clock`: `Clock` that returns the frozen now.
`in_memory_audit_repo`: M2 in-memory adapter (M5 re-uses it).
`hs256_signer`: pre-built HS256 signer with a fixed secret.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.application.audit_event.clock import Clock
from src.application.auth.signer import HS256JwtSigner
from src.domain.ports.audit_logs import AuditLogRepository
from src.infrastructure.repositories.in_memory.audit_logs import (
    InMemoryAuditLogRepository,
)


_SECRET = b"test-secret-do-not-use-in-prod-32-bytes!"


@pytest.fixture
def frozen_now() -> datetime:
    return datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def seed_clock(frozen_now: datetime) -> Clock:
    class _Clock:
        def now(self) -> datetime:
            return frozen_now

    return _Clock()


@pytest.fixture
def in_memory_audit_repo() -> AuditLogRepository:
    return InMemoryAuditLogRepository()


@pytest.fixture
def hs256_signer() -> HS256JwtSigner:
    return HS256JwtSigner(secret=_SECRET)


@pytest.fixture
def alt_hs256_signer() -> HS256JwtSigner:
    return HS256JwtSigner(secret=b"another-secret-not-the-real-one-32b!")
