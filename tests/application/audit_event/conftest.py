"""Fixtures for the audit-event use-case tests.

`audit_repo` is the in-memory adapter only. M4 ships no
pool/runtime wiring per D-031 / D-032; the use case is
exercised against the M2 in-memory adapter and against the
Postgres adapter via the `tests/infrastructure/repositories/`
parity suite (which already covers `append()` end-to-end
through both adapters).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from src.application.audit_event.dto import RecordAuditCommand
from src.application.audit_event.errors import PersistenceFailure
from src.application.audit_event.record import RecordAuditEvent
from src.application.audit_event.clock import Clock
from src.domain.ports.audit_logs import AuditDecision, AuditLogRepository
from src.domain.ports.errors import PersistenceError
from src.infrastructure.repositories.in_memory.audit_logs import (
    InMemoryAuditLogRepository,
)


class FrozenClock:
    """Deterministic clock for tests."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed


class ExplodingAuditLogRepository:
    """Probe repository: every `append` raises `PersistenceError`.

    Lets the test assert the use-case boundary handler without
    a real database.
    """

    def __init__(self, message: str = "explode") -> None:
        self._message = message
        self.calls = 0

    async def append(self, event):
        self.calls += 1
        raise PersistenceError(self._message)

    async def find_by_correlation_id(self, correlation_id):
        return []


@pytest.fixture
def frozen_now() -> datetime:
    return datetime(2026, 6, 20, tzinfo=timezone.utc)


@pytest.fixture
def clock(frozen_now: datetime) -> Clock:
    return FrozenClock(frozen_now)


@pytest.fixture
def audit_repo() -> AuditLogRepository:
    return InMemoryAuditLogRepository()


@pytest.fixture
def exploding_repo() -> ExplodingAuditLogRepository:
    return ExplodingAuditLogRepository()


@pytest.fixture
def record_use_case(audit_repo, clock) -> RecordAuditEvent:
    return RecordAuditEvent(audit_repo, clock=clock)


@pytest.fixture
def record_use_case_exploding(exploding_repo, clock) -> RecordAuditEvent:
    return RecordAuditEvent(exploding_repo, clock=clock)


@pytest.fixture
def make_cmd():
    """Factory for `RecordAuditCommand` with sensible defaults."""

    def _make(**overrides):
        defaults = {
            "actor_user_id": None,
            "action": "access.evaluated",
            "resource_type": None,
            "resource_id": None,
            "decision": AuditDecision.ALLOWED,
            "reason_code": "allowed",
            "correlation_id": "cid-test-01",
            "metadata": {"k": "v"},
        }
        defaults.update(overrides)
        return RecordAuditCommand(**defaults)

    return _make
