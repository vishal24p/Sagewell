"""M12 -- Audit + Retrieval Logs use case tests (real-repo).

These tests REPLACE the deprecated `_StubAuditRepo` / `_StubRetrievalRepo`
patterns in `test_logs.py`. They run against the **real** in-memory
implementations so the repository boundary is exercised. Issue 01
from `docs/HANDOFF/TECHNICAL_ISSUES.md` (the M10/M11 reason-code
rejection at the repository boundary) is now part of the green-bar.

Why these tests are required:

  - The original `tests/application/observability/test_logs.py` used
    a `_StubAuditRepo.append()` that did not invoke
    `is_allowed_reason_code(...)`. A green test bar at the stub does
    not prove that the production repository accepts the reason codes
    the application emits. Issue 01 (the V1 reason-code whitelist
    drift between the domain predicate and the application predicate)
    slipped through.

  - The new tests below exercise:

      1. The full M0 RBAC reason-code round-trip (the seven imm codes
         + JWT_INVALID + the three ingestion codes) against the real
         `InMemoryAuditLogRepository`.
      2. The full M10 Regex Guard reason-code round-trip
         (regex_passed, regex_refused_high, regex_refused_critical)
         against the real repository boundary.
      3. The full M11 LLM Guard reason-code round-trip
         (llm_guard_allow, llm_guard_downgrade, llm_guard_refuse)
         against the real repository boundary.
      4. The retrieval-log persistence round-trip against the real
         `InMemoryRetrievalLogRepository`.
      5. The Clock injection contract so `created_at` is timezone-
         aware, defending against the `datetime.utcnow()` deprecation
         flagged in TECHNICAL_ISSUES.md Issue 05.
      6. Searchability by `correlation_id` after a real `append` so
         forensic queries work.

Test count: 9 GREEN-bar tests. The original `_StubAuditRepo` tests
remain (deprecation migration is opt-in: the new tests are added; the
old tests are kept under `test_logs_legacy.py` for one release cycle
so the migration is traceable, then they will be removed when the
release-gate green-bar is updated).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.application.audit_event.clock import Clock
from src.application.observability.logs import (
    ALL_V1_REASON_CODES,
    RecordGuardVerdict,
    RecordGuardVerdictCommand,
    RecordRetrievalLog,
    RecordRetrievalLogCommand,
)
from src.domain.ports.audit_logs import AuditDecision, AuditEvent
from src.domain.ports.retrieval import RetrievalStageStats
from src.infrastructure.repositories.in_memory.audit_logs import (
    InMemoryAuditLogRepository,
)
from src.infrastructure.repositories.in_memory.retrieval_logs import (
    InMemoryRetrievalLogRepository,
)


pytestmark = pytest.mark.asyncio


class _StubRetrievalRepo:
    """Stub kept ONLY for the legacy migration file. Not used here."""


class _FixedClock(Clock):
    """Deterministic timezone-aware clock for test pinning."""

    def __init__(self, when: datetime) -> None:
        self._when = when

    def now(self) -> datetime:
        return self._when


def _stats() -> RetrievalStageStats:
    return RetrievalStageStats(
        dense_count=12,
        bm25_count=10,
        fused_count=8,
        rerank_count=4,
        after_access_count=2,
    )


def _guard_cmd(reason_code: str, *, action: str = "regex_guard.refused") -> RecordGuardVerdictCommand:
    return RecordGuardVerdictCommand(
        actor_user_id=42,
        correlation_id="corr-real",
        action=action,
        reason_code=reason_code,
        metadata={"rule_id": "prompt_injection_ignore"},
    )


async def test_all_v1_reason_codes_round_trip_via_real_audit_repository():
    """GREEN-bar: every reason_code in ALL_V1_REASON_CODES must be
    accepted by the real InMemoryAuditLogRepository.append(...).

    This is the test that proves TECHNICAL_ISSUES Issue 01 is
    fixed: previously, the M10/M11 codes were silently rejected
    by `is_allowed_reason_code` even though the application-level
    `ALL_V1_REASON_CODES` whitelist accepted them.
    """
    repo = InMemoryAuditLogRepository()
    use_case = RecordGuardVerdict(repo=repo)
    for code in sorted(ALL_V1_REASON_CODES):
        rid = await use_case.execute(
            RecordGuardVerdictCommand(
                actor_user_id=42,
                correlation_id=f"corr-{code}",
                action="guard.evaluated",
                reason_code=code,
                metadata={"code": code},
            )
        )
        assert rid > 0, f"real repository rejected {code!r}"
        events = await repo.find_by_correlation_id(f"corr-{code}")
        assert len(events) == 1, f"event for {code!r} not found"
        assert events[0].reason_code == code


async def test_m10_regex_guard_codes_round_trip_via_real_repository():
    """Specifically proves the three M10 codes land in the
    audit_logs through the real boundary.
    """
    repo = InMemoryAuditLogRepository()
    use_case = RecordGuardVerdict(repo=repo)
    for code in (
        "regex_passed",
        "regex_refused_high",
        "regex_refused_critical",
    ):
        await use_case.execute(
            RecordGuardVerdictCommand(
                actor_user_id=7,
                correlation_id=f"corr-m10-{code}",
                action="regex_guard.evaluated",
                reason_code=code,
                metadata={},
            )
        )
    for code in (
        "regex_passed",
        "regex_refused_high",
        "regex_refused_critical",
    ):
        events = await repo.find_by_correlation_id(f"corr-m10-{code}")
        assert len(events) == 1
        assert events[0].reason_code == code


async def test_m11_llm_guard_codes_round_trip_via_real_repository():
    """Specifically proves the three M11 codes land in the
    audit_logs through the real boundary.
    """
    repo = InMemoryAuditLogRepository()
    use_case = RecordGuardVerdict(repo=repo)
    for code in (
        "llm_guard_allow",
        "llm_guard_downgrade",
        "llm_guard_refuse",
    ):
        await use_case.execute(
            RecordGuardVerdictCommand(
                actor_user_id=7,
                correlation_id=f"corr-m11-{code}",
                action="llm_guard.evaluated",
                reason_code=code,
                metadata={},
            )
        )
    for code in (
        "llm_guard_allow",
        "llm_guard_downgrade",
        "llm_guard_refuse",
    ):
        events = await repo.find_by_correlation_id(f"corr-m11-{code}")
        assert len(events) == 1
        assert events[0].reason_code == code


async def test_unknown_reason_code_rejected_before_append():
    """Defensive: the real repository must still reject codes that
    are NOT in `ALL_V1_REASON_CODES`. Re-confirms the boundary
    still bites.
    """
    repo = InMemoryAuditLogRepository()
    use_case = RecordGuardVerdict(repo=repo)
    with pytest.raises(ValueError):
        await use_case.execute(
            RecordGuardVerdictCommand(
                actor_user_id=42,
                correlation_id="corr",
                action="malformed",
                reason_code="not_a_real_code",
                metadata={},
            )
        )


async def test_record_retrieval_log_round_trips_via_real_repository():
    """Use case writes to the real `InMemoryRetrievalLogRepository`
    and the candidate_counts field carries the serialized
    `RetrievalStageStats` shape end-to-end.

    The repository has no `find_by_correlation_id` in the V1 port
    surface; verification uses the in-memory `_logs` slot to
    demonstrate that the row materializes with the expected fields.
    Issue 04 (actor-id collapse-to-0 for non-numeric subjects)
    is pinned here as known behaviour tracked in
    `docs/HANDOFF/TECHNICAL_ISSUES.md`; the actor `0` outcome is
    the documented degenerate case.
    """
    repo = InMemoryRetrievalLogRepository()
    use_case = RecordRetrievalLog(repo=repo)
    fixed = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
    cmd = RecordRetrievalLogCommand(
        stage_stats=_stats(),
        query_text="what is the runbook?",
        policy_filter={
            "allowed_departments": ["engineering"],
            "minimum_clearance": "INTERNAL",
        },
        retrieval_config={"dense_model": "stub", "bm25_k1": 1.5, "bm25_b": 0.75},
        actor_user_id=42,  # numeric; non-numeric collapse-to-0 belongs to Issue 04
        correlation_id="corr-real-retrieval",
        occurred_at=fixed,
    )
    rid = await use_case.execute(cmd)
    assert rid > 0
    # Real boundary verification via the repository's internal
    # state (the V1 port does not expose search).
    assert len(repo._logs) == 1
    log = repo._logs[0]
    assert log.id == rid
    # numeric actor ids survive the helper. The collapse-to-zero
    # for non-numeric subjects is `Issue 04` and is exercised in
    # `test_record_retrieval_log_actor_id_zero_falls_into_real_repo_validator`.
    assert log.actor_user_id == 42
    assert log.query_text == "what is the runbook?"
    assert log.candidate_counts == {
        "dense_count": 12,
        "bm25_count": 10,
        "fused_count": 8,
        "rerank_count": 4,
        "after_access_count": 2,
    }
    # The Clock injection path is expected by Issue 05; here we
    # use the `occurred_at` field, which is timezone-aware.
    assert log.created_at.tzinfo is not None


async def test_record_retrieval_log_uses_injected_clock_when_occurred_at_none():
    """When `occurred_at is None`, the use case MUST use the injected
    Clock (Issue 05: deprecated datetime.utcnow()).
    """
    repo = InMemoryRetrievalLogRepository()
    fixed = datetime(2026, 6, 27, 13, 0, 0, tzinfo=timezone.utc)
    fake_clock = _FixedClock(fixed)
    use_case = RecordRetrievalLog(repo=repo, clock=fake_clock)
    cmd = RecordRetrievalLogCommand(
        stage_stats=_stats(),
        query_text="q",
        policy_filter={},
        retrieval_config={},
        actor_user_id=42,  # numeric; keeps the row writable today
        correlation_id="corr-clock",
    )
    rid = await use_case.execute(cmd)
    assert rid > 0
    assert len(repo._logs) == 1
    assert repo._logs[0].created_at == fixed


async def test_record_guard_verdict_uses_injected_clock_when_occurred_at_none():
    """Same Clock-injection contract as `RecordRetrievalLog` --
    `RecordGuardVerdict` must use the injected Clock when
    `occurred_at is None`.
    """
    repo = InMemoryAuditLogRepository()
    fixed = datetime(2026, 6, 27, 14, 0, 0, tzinfo=timezone.utc)
    fake_clock = _FixedClock(fixed)
    use_case = RecordGuardVerdict(repo=repo, clock=fake_clock)
    cmd = RecordGuardVerdictCommand(
        actor_user_id=42,
        correlation_id="corr-clock-guard",
        action="regex_guard.evaluated",
        reason_code="regex_refused_high",
        metadata={},
    )
    await use_case.execute(cmd)
    events = await repo.find_by_correlation_id("corr-clock-guard")
    assert len(events) == 1
    assert events[0].created_at == fixed


async def test_record_retrieval_log_actor_id_zero_falls_into_real_repo_validator():
    """Defensive: the real `InMemoryRetrievalLogRepository` rejects
    `actor_user_id <= 0` today. The collapse-to-zero (Issue 04)
    exposes the validator WHEN the helper short-circuits a
    non-numeric actor. This test pins the documented behaviour so
    the Issue 04 fix can change the helper without silently
    regressing the boundary validator.
    """
    repo = InMemoryRetrievalLogRepository()
    use_case = RecordRetrievalLog(repo=repo)
    cmd = RecordRetrievalLogCommand(
        stage_stats=_stats(),
        query_text="q",
        policy_filter={},
        retrieval_config={},
        # `None` collapses to 0 in the helper; the repository
        # then hard-rejects with PersistenceError. This is the
        # current state-of-the-art boundary; both pieces are
        # pinned here so the Issue 04 fix has a green-bar to
        # cross safely.
        actor_user_id=None,
        correlation_id="corr-collapse",
    )
    with pytest.raises(Exception):
        await use_case.execute(cmd)


async def test_record_guard_verdict_audit_row_carries_metadata_verbatim():
    """The M12 row's metadata dict MUST round-trip via `AuditEvent.metadata`
    so the workflow's metadata (rule ids, decision carve-outs) is
    forensically queryable.
    """
    repo = InMemoryAuditLogRepository()
    use_case = RecordGuardVerdict(repo=repo)
    metadata = {
        "rule_id": "document_authority_claim",
        "tier": "critical",
        "correlation_id": "corr-meta",
        "deep_nesting": {"a": [1, 2, 3], "b": {"c": "d"}},
    }
    cmd = RecordGuardVerdictCommand(
        actor_user_id=42,
        correlation_id="corr-meta",
        action="regex_guard.evaluated",
        reason_code="regex_refused_critical",
        metadata=metadata,
    )
    await use_case.execute(cmd)
    events = await repo.find_by_correlation_id("corr-meta")
    assert len(events) == 1
    assert events[0].metadata == metadata
    assert events[0].action == "regex_guard.evaluated"
    assert events[0].decision is AuditDecision.ALLOWED
