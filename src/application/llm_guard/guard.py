"""M11 -- LLM Guard application orchestrator.

The `LLMGuard` use case wraps the capability-shaped
`GuardrailModelPort`. It receives the (query, retrieved
chunks) bundle and returns a typed verdict +
reason-code envelope. The workflow boundary translates
the verdict:

  - ALLOW -> continue to generation.
  - DOWNGRADE -> demote the affected chunks; continue to
    generation with reduced citation set.
  - REFUSE -> return 400-class envelope at the API
    boundary; log an audit row.

The use case is async; calls the model port async. The
test surface uses an in-memory stub model.

Reason codes:

  - `llm_guard_allow` -> no contextual risk.
  - `llm_guard_downgrade` -> demote N chunks; continue.
  - `llm_guard_refuse` -> hard refusal; no generation.

The use case does not write audit rows; the workflow
boundary records the reason code + verdict rationale
through M4's `RecordAuditEvent`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.domain.ports.llm_guard import (
    GuardrailInput,
    GuardrailModelPort,
    GuardrailVerdict,
    LLMGuardCommand,
    LLMGuardResult,
    REASON_GUARD_ALLOW,
    REASON_GUARD_DOWNGRADE,
    REASON_GUARD_REFUSE,
)


__all__ = [
    "LLMGuard",
    "LLMGuardError",
]


class LLMGuardError(Exception):
    """Base M11 typed error."""

    code: str = "llm_guard_failure"


class LLMGuardUnavailableError(LLMGuardError):
    code: str = "llm_guard_unavailable"


@dataclass(frozen=True)
class LLMGuardEmptyInputError(LLMGuardError):
    """Raised when the LLM Guard receives an empty input."""

    code: str = "llm_guard_empty_input"


class LLMGuard:
    """M11 LLM Guard use case.

    `execute(command)` invokes the configured
    `GuardrailModelPort` with the typed input and
    returns the typed `LLMGuardResult`. The model port
    is injected; production wiring uses the hosted
    Guardrail Model adapter (open question D-004 owns
    the adoption milestone). Tests inject a stub.
    """

    def __init__(self, *, model: GuardrailModelPort) -> None:
        self._model = model

    async def execute(self, command: LLMGuardCommand) -> LLMGuardResult:
        if not command.query or not command.query.strip():
            raise LLMGuardEmptyInputError(
                "LLM Guard requires a non-blank query."
            )
        guard_input = GuardrailInput(
            query=command.query.strip(),
            chunk_quotes=tuple(command.chunk_quotes),
            chunk_ids=tuple(command.chunk_ids),
        )
        try:
            verdict: GuardrailVerdict = await self._model.classify(guard_input)
        except Exception as exc:  # pragma: no cover -- port-side failures are typed
            raise LLMGuardUnavailableError(
                "Guardrail Model classify failed; LLM Guard is unavailable."
            ) from exc

        reason_code = _reason_code_for(verdict)
        affected = (
            tuple(verdict.dropped_chunk_ids)
            if verdict.classification.value == "downgrade"
            else ()
        )
        return LLMGuardResult(
            verdict=verdict,
            reason_code=reason_code,
            correlation_id=command.context_correlation_id,
            affected_chunk_ids=affected,
        )


def _reason_code_for(verdict: GuardrailVerdict) -> str:
    if verdict.classification.value == "refuse":
        return REASON_GUARD_REFUSE
    if verdict.classification.value == "downgrade":
        return REASON_GUARD_DOWNGRADE
    return REASON_GUARD_ALLOW
