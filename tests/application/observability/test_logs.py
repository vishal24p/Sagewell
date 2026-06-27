"""M12 Audit + Retrieval Logs complete use case tests.

Six tests:

1. happy_record_retrieval_log.
2. retrieval_log_without_state_round_trips_via_repository.
3. record_guard_verdict_writes_audit_row.
4. record_guard_verdict_rejects_unknown_reason_codes.
5. all_v1_reason_codes_include_m10_m11_m12.
6. all_v1_reason_codes_include_m0_m5_m7_for_backwards_compat.
"""
from __future__ import annotations

import asyncio
import dataclasses

import pytest

from src.application.observability.logs import (
    ALL_V1_REASON_CODES,
    RecordGuardVerdict,
    RecordGuardVerdictCommand,
    RecordRetrievalLog,
    RecordRetrievalLogCommand,
)
from src.domain.ports.audit_logs import AuditDecision, AuditEvent
from src.domain.ports.retrieval import RetrievalStageStats
from src.domain.ports.retrieval_logs import RetrievalLog


# Stubs for repos; the M12 use cases call append() on these.

class _StubRetrievalRepo:
    def __init__(self):
        self.last: RetrievalLog = None  # type: ignore[assignment]
        self.next_id = 1

    async def append(self, log: RetrievalLog) -> int:
        self.last = log
        rid = self.next_id
        self.next_id += 1
        return rid


class _StubAuditRepo:
    def __init__(self):
        self.lasts: list[AuditEvent] = []
        self.next_id = 1

    async def append(self, audit: AuditEvent) -> int:
        self.lasts.append(audit)
        rid = self.next_id
        self.next_id += 1
        return rid


pytestmark = pytest.mark.asyncio


def _actor_id():
    return "42"


def _stats():
    return RetrievalStageStats(
        dense_count=12,
        bm25_count=10,
        fused_count=8,
        rerank_count=4,
        after_access_count=2,
    )


async def test_happy_record_retrieval_log():
    repo = _StubRetrievalRepo()
    use_case = RecordRetrievalLog(repo=repo)
    cmd = RecordRetrievalLogCommand(
        stage_stats=_stats(),
        query_text="what is the runbook",
        policy_filter={"allowed_departments": ["engineering"], "minimum_clearance": "INTERNAL"},
        retrieval_config={"dense_model": "stub", "bm25_k1": 1.5, "bm25_b": 0.75},
        actor_user_id=_actor_id(),
        correlation_id="corr-m12",
    )
    rid = await use_case.execute(cmd)
    assert rid == 1
    log = repo.last
    assert log.actor_user_id == 42
    assert log.query_text == "what is the runbook"
    assert log.candidate_counts == {
        "dense_count": 12,
        "bm25_count": 10,
        "fused_count": 8,
        "rerank_count": 4,
        "after_access_count": 2,
    }
    assert log.correlation_id == "corr-m12"


async def test_unknown_actor_falls_back_to_zero():
    repo = _StubRetrievalRepo()
    use_case = RecordRetrievalLog(repo=repo)
    cmd = RecordRetrievalLogCommand(
        stage_stats=_stats(),
        query_text="q",
        policy_filter={},
        retrieval_config={},
        actor_user_id="notanumber",
        correlation_id="corr",
    )
    await use_case.execute(cmd)
    assert repo.last.actor_user_id == 0


async def test_record_guard_verdict_writes_audit_row():
    repo = _StubAuditRepo()
    use_case = RecordGuardVerdict(repo=repo)
    cmd = RecordGuardVerdictCommand(
        actor_user_id=42,
        correlation_id="corr-m12",
        action="regex_guard.refused",
        reason_code="regex_refused_high",
        metadata={"rule_id": "prompt_injection_ignore"},
    )
    rid = await use_case.execute(cmd)
    assert rid == 1
    audit = repo.lasts[0]
    assert audit.action == "regex_guard.refused"
    assert audit.reason_code == "regex_refused_high"
    assert audit.decision is AuditDecision.ALLOWED


async def test_record_guard_verdict_rejects_unknown_reason_codes():
    repo = _StubAuditRepo()
    use_case = RecordGuardVerdict(repo=repo)
    cmd = RecordGuardVerdictCommand(
        actor_user_id=42,
        correlation_id="corr",
        action="regex_guard.refused",
        reason_code="not_a_real_code",
        metadata={},
    )
    with pytest.raises(ValueError):
        await use_case.execute(cmd)


async def test_all_v1_reason_codes_include_m10_m11_m12():
    assert "regex_passed" in ALL_V1_REASON_CODES
    assert "regex_refused_high" in ALL_V1_REASON_CODES
    assert "regex_refused_critical" in ALL_V1_REASON_CODES
    assert "llm_guard_allow" in ALL_V1_REASON_CODES
    assert "llm_guard_downgrade" in ALL_V1_REASON_CODES
    assert "llm_guard_refuse" in ALL_V1_REASON_CODES


async def test_all_v1_reason_codes_include_m0_m5_m7():
    # The M0 imm codes remain.
    for code in (
        "missing_user_department",
        "missing_user_clearance",
        "missing_document_department",
        "missing_document_clearance",
        "department_mismatch",
        "clearance_insufficient",
        "allowed",
    ):
        assert code in ALL_V1_REASON_CODES
    # M5 (jwt_invalid) and M7 ingestion are still allowed.
    for code in (
        "jwt_invalid",
        "ingestion_succeeded",
        "ingestion_skipped",
        "ingestion_failed",
    ):
        assert code in ALL_V1_REASON_CODES
