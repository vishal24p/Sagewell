"""
Parity tests for EvaluationResultRepository.

suite is restricted to {'ragas', 'rbac_access_outcome'}.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

import pytest

from src.domain.ports.errors import PersistenceError
from src.domain.ports.evaluation_results import (
    EvaluationResult,
    EvaluationStatus,
    Suite,
)


def _result(suite: Suite = Suite.RAGAS) -> EvaluationResult:
    return EvaluationResult(
        id=None,
        suite=suite,
        case_key="case-1",
        input={"q": "test"},
        expected={"a": "expected"},
        status=EvaluationStatus.PASSED,
        scores={"faithfulness": 0.9},
        failure_reason=None,
        model_config={"embedding": "capability"},
        created_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
    )


class TestEvaluationResultRepository:
    @pytest.fixture
    async def eval_repo(self, adapter, clean_postgres_state):
        backend, factory, pool = adapter
        _user, _doc, _chunk, _audit, _log, eval_repo = factory(pool)
        return eval_repo

    async def test_record_runs_assign_id(self, eval_repo):
        new_id = await eval_repo.record(_result())
        assert new_id > 0

    async def test_list_by_suite_filters(self, eval_repo):
        await eval_repo.record(_result(Suite.RAGAS))
        await eval_repo.record(_result(Suite.RBAC_ACCESS_OUTCOME))
        ragas = await eval_repo.list_by_suite(Suite.RAGAS)
        rbac = await eval_repo.list_by_suite(Suite.RBAC_ACCESS_OUTCOME)
        assert len(ragas) == 1
        assert len(rbac) == 1
        assert ragas[0].suite == Suite.RAGAS
        assert rbac[0].suite == Suite.RBAC_ACCESS_OUTCOME

    async def test_record_rejects_unknown_suite_value(self, eval_repo):
        # Build a properly-typed EvaluationResult, then override
        # `suite` after construction with a string that is outside
        # the enum's allowed values. The dataclass `EvaluationResult`
        # is `frozen=True`; bypass the frozen guard once via
        # `object.__setattr__`. The adapter's validator is the
        # single rejection boundary for this case across both
        # backends: `Suite` enum construction is not on the path.
        good = _result()
        bad = EvaluationResult(
            id=good.id,
            suite=good.suite,
            case_key="bad",
            input={},
            expected={},
            status=good.status,
            scores={},
            failure_reason=None,
            model_config={},
            created_at=good.created_at,
        )
        object.__setattr__(bad, "suite", cast(Suite, "hypothetical_suite"))
        assert bad.suite == "hypothetical_suite"
        with pytest.raises(PersistenceError):
            await eval_repo.record(bad)
