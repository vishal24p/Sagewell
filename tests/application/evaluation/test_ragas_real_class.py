"""M13 -- RAGAS evaluation realistic stub (no field shadowing).

This file REPLACES the deprecated `_StubScorer` pattern in
`tests/application/evaluation/test_ragas.py` that shadowed
`self.score` on the same name as the method `score()`. The
deprecated pattern made the field carry an `RagasScore` and
the method return the same instance, allowing a future rename
of the method to silently keep passing.

The replacement tests use a small named-class helper with
unambiguous fields (`_fixed_score`, `_next_score`) and a real
`score` method. The contract (every threshold rule) is
re-asserted against the real DTO `/ result / verdict` types.
"""
from __future__ import annotations

import pytest

from src.application.evaluation.ragas import (
    RunRagasCase,
    RunRagasCaseCommand,
)
from src.domain.ports.ragas import (
    RagasCase,
    RagasMetric,
    RagasScore,
    RagasScorerPort,
    RagasVerdict,
)


class _RealisticScorer:
    """Stub scorer with unambiguous field names."""

    def __init__(
        self,
        scores_by_metric: dict[RagasMetric, float],
        rationale: str = "realistic stub run",
    ) -> None:
        self._fixed_scores = dict(scores_by_metric)
        self._rationale = rationale
        # `self.last_case` collides with method names so avoid it.
        self.received_case: RagasCase | None = None

    async def score(self, case: RagasCase) -> RagasScore:
        self.received_case = case
        return RagasScore(
            metrics=self._fixed_scores,
            rationale=self._rationale,
        )


pytestmark = pytest.mark.asyncio


def _case(minimums=None):
    return RagasCase(
        case_key="case-real-stub",
        query="what is the runbook?",
        answer="use the runbook.",
        retrieved_contexts=("runbook line 1", "runbook line 2"),
        ground_truth_contexts=("runbook line 1",),
        ground_truth_answer="use the runbook.",
        minimums=minimums or {},
    )


def _cmd(case: RagasCase) -> RunRagasCaseCommand:
    return RunRagasCaseCommand(case=case)


async def test_realistic_scorer_returns_typed_ragas_score():
    """The stub returns a typed `RagasScore`. The use case
    routes it through the threshold rule without losing types.
    """
    scorer = _RealisticScorer(
        scores_by_metric={
            RagasMetric.FAITHFULNESS: 0.9,
            RagasMetric.CONTEXT_PRECISION: 0.8,
            RagasMetric.CONTEXT_RECALL: 0.7,
            RagasMetric.ANSWER_RELEVANCY: 0.85,
        },
        rationale="realistic stub run",
    )
    use_case = RunRagasCase(scorer=scorer)
    verdict = await use_case.execute(_cmd(_case()))
    assert verdict.passed is True
    # `failure_reason` is None when verdict passes; some other
    # shape would fail the test as a regression.
    assert not verdict.failure_reason
    assert scorer.received_case is not None
    assert scorer.received_case.case_key == "case-real-stub"


async def test_realistic_scorer_threshold_breach_returns_typed_verdict():
    """One metric falls below the threshold -> verdict.passed
    is False; failure_reason names the breach.
    """
    scorer = _RealisticScorer(
        scores_by_metric={
            RagasMetric.FAITHFULNESS: 0.9,
            RagasMetric.CONTEXT_PRECISION: 0.4,  # breach
            RagasMetric.CONTEXT_RECALL: 0.7,
            RagasMetric.ANSWER_RELEVANCY: 0.85,
        },
    )
    use_case = RunRagasCase(scorer=scorer)
    verdict = await use_case.execute(
        _cmd(
            _case(
                minimums={
                    RagasMetric.FAITHFULNESS: 0.8,
                    RagasMetric.CONTEXT_PRECISION: 0.6,
                    RagasMetric.CONTEXT_RECALL: 0.6,
                    RagasMetric.ANSWER_RELEVANCY: 0.8,
                }
            )
        )
    )
    assert verdict.passed is False
    assert "context_precision" in verdict.failure_reason


async def test_realistic_scorer_exposes_protocol_surface():
    """The realistic stub exposes the same `score` method the
    production adapter must provide. Confirming via
    `callable(getattr(scorer, 'score'))` keeps the test
    pure (no runtime Protocol check needed).
    """
    scorer = _RealisticScorer(
        scores_by_metric={RagasMetric.FAITHFULNESS: 1.0},
    )
    assert callable(getattr(scorer, "score", None)) is True
    use_case = RunRagasCase(scorer=scorer)
    verdict = await use_case.execute(
        _cmd(_case(minimums={RagasMetric.FAITHFULNESS: 0.5}))
    )
    assert verdict.passed is True
