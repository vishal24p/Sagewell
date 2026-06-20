"""
Parity tests for AuditLogRepository.

The repository enforces the V1 reason-code whitelist at append time.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.domain.ports.audit_logs import AuditDecision, AuditEvent
from src.domain.ports.errors import PersistenceError


def _event(
    correlation_id: str = "corr-1",
    *,
    reason_code: str = "department_mismatch",
    decision: AuditDecision = AuditDecision.DENIED,
    action: str = "access.evaluated",
) -> AuditEvent:
    return AuditEvent(
        id=None,
        actor_user_id=1,
        action=action,
        resource_type="document",
        resource_id="42",
        decision=decision,
        reason_code=reason_code,
        correlation_id=correlation_id,
        metadata={"redacted": True},
        created_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
    )


class TestAuditLogRepository:
    @pytest.fixture
    async def audit_repo(self, adapter, seed_parent_rows):
        backend, factory, pool = adapter
        _user, _doc, _chunk, audit, *_ = factory(pool)
        return audit

    async def test_append_assigns_id_and_stores_row(self, audit_repo):
        audit = audit_repo
        new_id = await audit.append(_event())
        assert new_id > 0
        events = await audit.find_by_correlation_id("corr-1")
        assert len(events) == 1
        assert events[0].reason_code == "department_mismatch"
        assert events[0].decision == AuditDecision.DENIED

    async def test_find_by_correlation_id_returns_empty_when_missing(self, audit_repo):
        events = await audit_repo.find_by_correlation_id("never-seen")
        assert events == []

    async def test_append_rejects_unknown_reason_code(self, audit_repo):
        with pytest.raises(PersistenceError):
            await audit_repo.append(_event(reason_code="JWT_INVALID"))

    async def test_append_rejects_empty_correlation_id(self, audit_repo):
        with pytest.raises(PersistenceError):
            await audit_repo.append(_event(correlation_id=""))

    async def test_m0_imm_codes_round_trip(self, audit_repo):
        for code in (
            "missing_user_department",
            "missing_user_clearance",
            "missing_document_department",
            "missing_document_clearance",
            "department_mismatch",
            "clearance_insufficient",
            "allowed",
        ):
            await audit_repo.append(
                _event(correlation_id=f"corr-{code}", reason_code=code)
            )
        events = await audit_repo.find_by_correlation_id("corr-allowed")
        assert events[0].reason_code == "allowed"
