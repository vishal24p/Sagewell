"""M11 LLM Guard application use case tests.

Five tests:

1. happy_allow_returns_typed_result.
2. downgrade_returns_demoted_chunk_ids.
3. refuse_returns_reason_code.
4. empty_query_raises_typed_error.
5. model_failure_raises_unavailable.
"""
from __future__ import annotations

import pytest

from src.application.llm_guard.guard import (
    LLMGuard,
    LLMGuardEmptyInputError,
    LLMGuardUnavailableError,
)
from src.domain.ports.llm_guard import (
    GuardrailClassification,
    GuardrailInput,
    GuardrailModelPort,
    GuardrailVerdict,
    LLMGuardCommand,
)


class _StubModel:
    """In-memory guardrail model stub."""

    def __init__(self, verdict: GuardrailVerdict) -> None:
        self.verdict = verdict
        self.last_input: GuardrailInput = None  # type: ignore[assignment]

    async def classify(self, guard_input: GuardrailInput) -> GuardrailVerdict:
        self.last_input = guard_input
        return self.verdict


class _BoomModel:
    """A model that raises during classify()."""

    async def classify(self, guard_input):
        raise RuntimeError("guardrail timeout")


pytestmark = pytest.mark.asyncio


def _cmd(query: str = "What is the runbook?"):
    return LLMGuardCommand(
        query=query,
        chunk_ids=(11, 22),
        chunk_quotes=("q1", "q2"),
        context_correlation_id="corr-m11",
    )


async def test_happy_allow_returns_typed_result():
    model = _StubModel(
        GuardrailVerdict(
            classification=GuardrailClassification.ALLOW,
            rationale="no contextual risk",
        )
    )
    guard = LLMGuard(model=model)
    result = await guard.execute(_cmd())
    assert result.verdict.classification is GuardrailClassification.ALLOW
    assert result.reason_code == "llm_guard_allow"
    assert result.affected_chunk_ids == ()


async def test_downgrade_returns_demoted_chunk_ids():
    model = _StubModel(
        GuardrailVerdict(
            classification=GuardrailClassification.DOWNGRADE,
            rationale="chunk 11 contains suspicious instruction",
            dropped_chunk_ids=(11,),
        )
    )
    guard = LLMGuard(model=model)
    result = await guard.execute(_cmd())
    assert result.verdict.classification is GuardrailClassification.DOWNGRADE
    assert result.reason_code == "llm_guard_downgrade"
    assert result.affected_chunk_ids == (11,)


async def test_refuse_returns_reason_code():
    model = _StubModel(
        GuardrailVerdict(
            classification=GuardrailClassification.REFUSE,
            rationale="bundle contains a hidden instruction",
        )
    )
    guard = LLMGuard(model=model)
    result = await guard.execute(_cmd())
    assert result.verdict.classification is GuardrailClassification.REFUSE
    assert result.reason_code == "llm_guard_refuse"
    assert result.affected_chunk_ids == ()


async def test_empty_query_raises_typed_error():
    guard = LLMGuard(model=_StubModel(
        GuardrailVerdict(
            classification=GuardrailClassification.ALLOW,
            rationale="unused",
        )
    ))
    with pytest.raises(LLMGuardEmptyInputError):
        await guard.execute(_cmd(query="   "))


async def test_model_failure_raises_unavailable():
    guard = LLMGuard(model=_BoomModel())
    with pytest.raises(LLMGuardUnavailableError):
        await guard.execute(_cmd())
