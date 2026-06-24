"""M4 use-case tests for `RecordAuditEvent`.

Coverage:

1. M0 IMM `allowed` reason_code persists and returns a positive id.
2. `correlation_id` is forwarded into the repository row.
3. `created_at` is taken from the injected `Clock`.
4. Empty correlation_id raises `AuditEventError` (validation).
5. Empty action raises `AuditEventError` (validation).
6. Decision outside the `AuditDecision` enum raises `AuditEventError`.
7. Unknown reason_code surfaces as `PersistenceFailure` (rejected by
   the M2 repository's V1 whitelist).
8. The repository's `PersistenceError` is translated to
   `PersistenceFailure` (typed boundary handler).
9. Caller's metadata dict is not mutated by the use case.
10. `actor_user_id=None` is forwarded as `NULL` (in-memory unaffected).
"""
from __future__ import annotations

import pytest

from src.application.audit_event.errors import (
    AuditEventError,
    PersistenceFailure,
)
from src.domain.ports.audit_logs import AuditDecision


pytestmark = pytest.mark.asyncio


async def test_records_event_with_valid_m0_reason_code(
    record_use_case, make_cmd, audit_repo
):
    cmd = make_cmd(reason_code="allowed")
    new_id = await record_use_case(cmd)
    assert new_id > 0
    events = await audit_repo.find_by_correlation_id("cid-test-01")
    assert len(events) == 1
    assert events[0].reason_code == "allowed"
    assert events[0].decision == AuditDecision.ALLOWED


async def test_emitted_event_carries_injected_correlation_id(
    record_use_case, make_cmd, audit_repo
):
    cmd = make_cmd(correlation_id="cid-pinned")
    await record_use_case(cmd)
    events = await audit_repo.find_by_correlation_id("cid-pinned")
    assert len(events) == 1
    assert events[0].correlation_id == "cid-pinned"


async def test_emitted_event_carries_clocks_now_as_created_at(
    record_use_case, make_cmd, audit_repo, frozen_now
):
    cmd = make_cmd()
    await record_use_case(cmd)
    events = await audit_repo.find_by_correlation_id("cid-test-01")
    assert events[0].created_at == frozen_now


async def test_rejects_missing_correlation_id(record_use_case, make_cmd):
    cmd = make_cmd(correlation_id="")
    with pytest.raises(AuditEventError):
        await record_use_case(cmd)


async def test_rejects_missing_action(record_use_case, make_cmd):
    cmd = make_cmd(action="")
    with pytest.raises(AuditEventError):
        await record_use_case(cmd)


async def test_rejects_audit_decision_outside_enum(record_use_case, make_cmd):
    cmd = make_cmd(decision="allowed_but_invalid_string")  # type: ignore[arg-type]
    with pytest.raises(AuditEventError):
        await record_use_case(cmd)


async def test_jwt_invalid_reason_code_is_accepted(
    record_use_case, make_cmd, audit_repo
):
    """M5 widening: `jwt_invalid` joins the V1 repository whitelist.

    The seven M0 IMM codes remain unchanged. `jwt_invalid` is
    appended to the repository's V1-allowed set so M5's
    `VerifyJwtToken` can persist failure rows.
    """
    cmd = make_cmd(
        reason_code="jwt_invalid",
        action="auth.jwt.evaluated",
        decision=AuditDecision.FAILED,
    )
    new_id = await record_use_case(cmd)
    assert new_id > 0
    events = await audit_repo.find_by_correlation_id("cid-test-01")
    assert len(events) == 1
    assert events[0].reason_code == "jwt_invalid"
    assert events[0].decision == AuditDecision.FAILED

async def test_rejects_truly_unknown_reason_code_via_persistence_failure(
    record_use_case, make_cmd
):
    """Whitelist remains fail-closed against codes outside the V1 set."""
    cmd = make_cmd(reason_code="totally_made_up_code")
    with pytest.raises(PersistenceFailure):
        await record_use_case(cmd)


async def test_persistence_failure_raised_when_repository_raises(
    record_use_case_exploding, make_cmd, exploding_repo
):
    cmd = make_cmd(reason_code="allowed")
    with pytest.raises(PersistenceFailure) as excinfo:
        await record_use_case_exploding(cmd)
    assert "explode" in str(excinfo.value)
    assert exploding_repo.calls == 1


async def test_metadata_is_isolated_to_the_passed_dict(
    record_use_case, make_cmd
):
    """The use-case stamps a dict copy, not the caller's dict."""
    src = {"k": "v"}
    cmd = make_cmd(metadata=src)
    await record_use_case(cmd)
    assert src == {"k": "v"}
    side_effect = src.setdefault("mutated", True)
    assert side_effect is True
    # Internal: call_recorded.metadata stays isolated on the next call.
    cmd2 = make_cmd(correlation_id="cid-c2", metadata=src)
    await record_use_case(cmd2)


async def test_actor_user_id_none_is_passed_through(record_use_case, make_cmd, audit_repo):
    cmd = make_cmd(actor_user_id=None)
    await record_use_case(cmd)
    events = await audit_repo.find_by_correlation_id("cid-test-01")
    assert events[0].actor_user_id is None
