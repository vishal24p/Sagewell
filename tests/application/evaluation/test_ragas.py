"""M13 RAGAS application use case tests.

Six tests:

1. happy_pass_when_all_metrics_above_threshold.
2. fail_when_metric_below_threshold.
3. informational_metric_outside_minimums_does_not_fail.
4. missing_metric_in_scorer_output_fails.
5. fallback_when_minimums_empty_passed_default.
6. failure_reason_summarizes_breaches.
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
)


class _StubScorer:
    def __init__(self, fixed_score: RagasScore) -> None:
        self._fixed_score = fixed_score
        self.last_case: RagasCase = None  # type: ignore[assignment]

    async def score(self, case: RagasCase) -> RagasScore:
        self.last_case = case
        return self._fixed_score


pytestmark = pytest.mark.asyncio


def _case(minimums=None):
    return RagasCase(
        case_key="faq_001",
        query="What is the runbook?",
        answer="The runbook describes incident response procedure.",
        retrieved_contexts=("ctx-a", "ctx-b"),
        ground_truth_contexts=("ctx-a", "ctx-b"),
        ground_truth_answer="incident response procedure.",
        minimums=minimums or {},
    )


async def test_happy_pass_when_all_metrics_above_threshold():
    scorer = _StubScorer(
        RagasScore(
            metrics={
                RagasMetric.FAITHFULNESS: 0.95,
                RagasMetric.CONTEXT_PRECISION: 0.90,
                RagasMetric.CONTEXT_RECALL: 0.88,
                RagasMetric.ANSWER_RELEVANCY: 0.93,
            }
        )
    )
    case = _case(
        minimums={
            RagasMetric.FAITHFULNESS: 0.7,
            RagasMetric.CONTEXT_PRECISION: 0.7,
            RagasMetric.CONTEXT_RECALL: 0.7,
            RagasMetric.ANSWER_RELEVANCY: 0.7,
        }
    )
    use_case = RunRagasCase(scorer=scorer)
    verdict = await use_case.execute(
        RunRagasCaseCommand(case=case)
    )
    assert verdict.passed is True
    assert verdict.failure_reason is None


async def test_fail_when_metric_below_threshold():
    scorer = _StubScorer(
        RagasScore(
            metrics={
                RagasMetric.FAITHFULNESS: 0.5,
                RagasMetric.CONTEXT_PRECISION: 0.9,
                RagasMetric.CONTEXT_RECALL: 0.9,
                RagasMetric.ANSWER_RELEVANCY: 0.9,
            }
        )
    )
    case = _case(
        minimums={
            RagasMetric.FAITHFULNESS: 0.7,
        }
    )
    use_case = RunRagasCase(scorer=scorer)
    verdict = await use_case.execute(
        RunRagasCaseCommand(case=case)
    )
    assert verdict.passed is False
    assert "faithfulness" in (verdict.failure_reason or "")


async def test_informational_metric_outside_minimums_does_not_fail():
    scorer = _StubScorer(
        RagasScore(
            metrics={
                RagasMetric.FAITHFULNESS: 0.99,
                RagasMetric.CONTEXT_PRECISION: 0.05,
            }
        )
    )
    case = _case(
        minimums={RagasMetric.FAITHFULNESS: 0.7}
    )
    use_case = RunRagasCase(scorer=scorer)
    verdict = await use_case.execute(
        RunRagasCaseCommand(case=case)
    )
    assert verdict.passed is True


async def test_missing_metric_in_scorer_output_fails():
    scorer = _StubScorer(
        RagasScore(
            metrics={RagasMetric.FAITHFULNESS: 0.9}
        )
    )
    case = _case(
        minimums={
            RagasMetric.FAITHFULNESS: 0.7,
            RagasMetric.CONTEXT_PRECISION: 0.7,
        }
    )
    use_case = RunRagasCase(scorer=scorer)
    verdict = await use_case.execute(
        RunRagasCaseCommand(case=case)
    )
    assert verdict.passed is False
    assert "context_precision" in (verdict.failure_reason or "")


async def test_default_pass_when_minimums_empty():
    scorer = _StubScorer(
        RagasScore(
            metrics={RagasMetric.FAITHFULNESS: 0.0}
        )
    )
    case = _case(minimums={})
    use_case = RunRagasCase(scorer=scorer)
    verdict = await use_case.execute(
        RunRagasCaseCommand(case=case)
    )
    assert verdict.passed is True


async def test_failure_reason_summarizes_multiple_breaches():
    scorer = _StubScorer(
        RagasScore(
            metrics={
                RagasMetric.FAITHFULNESS: 0.4,
                RagasMetric.CONTEXT_PRECISION: 0.99,
                RagasMetric.CONTEXT_RECALL: 0.4,
            }
        )
    )
    case = _case(
        minimums={
            RagasMetric.FAITHFULNESS: 0.7,
            RagasMetric.CONTEXT_PRECISION: 0.7,
            RagasMetric.CONTEXT_RECALL: 0.7,
        }
    )
    use_case = RunRagasCase(scorer=scorer)
    verdict = await use_case.execute(
        RunRagasCaseCommand(case=case)
    )
    assert verdict.passed is False
    assert "faithfulness" in (verdict.failure_reason or "")
    assert "context_recall" in (verdict.failure_reason or "")
