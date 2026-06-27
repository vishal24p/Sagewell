"""M11 -- LLM Guard realistic stub (no field shadowing).

This file REPLACES the deprecated `_StubModel` pattern in
`tests/application/llm_guard/test_llm_guard.py`. The legacy
model stored `self.verdict = verdict` and method-overloaded
`async def classify(...)` -- a future naming change could
silently keep passing because the field and method names
collapse into the same Python identifier.

The replacement uses an unambiguous field name (`_next_verdict`)
so a method rename is detected immediately. The contract
(ALLOW / DOWNGRADE / REFUSE) is re-asserted against the real
typed DTO/result types.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.application.llm_guard.guard import (
    LLMGuard,
    LLMGuardEmptyInputError,
)
from src.domain.ports.llm_guard import (
    GuardrailClassification,
    GuardrailInput,
    GuardrailModelPort,
    GuardrailVerdict,
    LLMGuardCommand,
)


class _RealisticGuardrailModel:
    """Realistic stub with unambiguous names."""

    def __init__(self, next_verdict: GuardrailVerdict) -> None:
        # `next_verdict` (not `self.verdict`) avoids shadowing any
        # public attribute; `_last_input` makes receipt explicit.
        self._next_verdict: GuardrailVerdict = next_verdict
        self._last_input: GuardrailInput | None = None

    async def classify(self, guard_input: GuardrailInput) -> GuardrailVerdict:
        self._last_input = guard_input
        return self._next_verdict


class _BoomModel:
    async def classify(self, guard_input):
        raise RuntimeError("timeout")


def _cmd(query: str = "What is the runbook?") -> LLMGuardCommand:
    return LLMGuardCommand(
        query=query,
        chunk_ids=(11, 22),
        chunk_quotes=("q1", "q2"),
        context_correlation_id="corr-realistic",
    )


pytestmark = pytest.mark.asyncio


async def test_allow_returns_typed_result():
    model = _RealisticGuardrailModel(
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
    # The stub recorded the typed-input contract.
    assert model._last_input is not None
    assert model._last_input.chunk_ids == (11, 22)


async def test_downgrade_returns_typed_demoted_chunk_ids():
    model = _RealisticGuardrailModel(
        GuardrailVerdict(
            classification=GuardrailClassification.DOWNGRADE,
            rationale="chunk 11 suspicious",
            dropped_chunk_ids=(11,),
        )
    )
    guard = LLMGuard(model=model)
    result = await guard.execute(_cmd())
    assert result.verdict.classification is GuardrailClassification.DOWNGRADE
    assert result.reason_code == "llm_guard_downgrade"
    assert result.affected_chunk_ids == (11,)


async def test_refuse_returns_typed_result():
    model = _RealisticGuardrailModel(
        GuardrailVerdict(
            classification=GuardrailClassification.REFUSE,
            rationale="hidden instruction",
        )
    )
    guard = LLMGuard(model=model)
    result = await guard.execute(_cmd())
    assert result.verdict.classification is GuardrailClassification.REFUSE
    assert result.reason_code == "llm_guard_refuse"


async def test_empty_query_raises_typed_error():
    guard = LLMGuard(
        model=_RealisticGuardrailModel(
            GuardrailVerdict(
                classification=GuardrailClassification.ALLOW,
                rationale="unused",
            )
        )
    )
    with pytest.raises(LLMGuardEmptyInputError):
        await guard.execute(_cmd(query="   "))


async def test_model_failure_raises_typed_unavailable():
    guard = LLMGuard(model=_BoomModel())
    from src.application.llm_guard.guard import LLMGuardUnavailableError

    with pytest.raises(LLMGuardUnavailableError):
        await guard.execute(_cmd())
