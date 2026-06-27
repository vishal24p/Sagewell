"""M11 -- LLM Guard ports.

The LLM Guard is a context-aware prompt-protection
step per `POLICIES.md`. It runs AFTER retrieval and
BEFORE generation. The Guardrail Model classifies
the (query, retrieved chunks) bundle into one of
three verdicts:

  - `allow`: no contextual attack; the bundle may
    proceed to generation.
  - `downgrade`: a contextual risk is present; the
    bundle may proceed but with the affected chunks
    demoted (their text is summarized or excluded
    from the citation list).
  - `refuse`: a hard rejection; the bundle is not
    sent to the generation step; the workflow
    boundary returns a typed refusal.

The guard emits a typed verdict carrying the
classification, the rationale (human-readable),
and the affected chunk ids (when a downgrade
demotes specific items).

Ports:

  - `GuardrailVerdict`: typed outcome.
  - `GuardrailModelPort`: the capability-shaped
    protocol the Guardrail Model SDK implements.
    Capability-deferred: open question D-004 owns
    the adoption milestone. The application package
    imports the protocol only.
  - `LLMGuardCommand` / `LLMGuardResult`: the use-case
    command / result dataclasses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol, Sequence


class GuardrailClassification(str, Enum):
    ALLOW = "allow"
    DOWNGRADE = "downgrade"
    REFUSE = "refuse"


@dataclass(frozen=True)
class GuardrailVerdict:
    """The typed verdict from the Guardrail Model.

    - `classification`: ALLOW / DOWNGRADE / REFUSE.
    - `rationale`: required human-readable rationale
      so the audit row carries an explainable result.
    - `dropped_chunk_ids`: chunk ids the model
      recommends demoting. Empty when ALLOW; can be
      non-empty on DOWNGRADE; ignored on REFUSE.
    """

    classification: GuardrailClassification
    rationale: str
    dropped_chunk_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class GuardrailInput:
    """The contract the Guardrail Model receives."""

    query: str
    chunk_quotes: tuple[str, ...]
    chunk_ids: tuple[int, ...]


class GuardrailModelPort(Protocol):
    """The Guardrail Model capability.

    `classify(input)` returns a `GuardrailVerdict`. The
    implementation is the hosted-model adapter (open
    question D-004 owns the adoption milestone).
    """

    async def classify(self, guard_input: GuardrailInput) -> GuardrailVerdict: ...


@dataclass(frozen=True)
class LLMGuardCommand:
    """Typed command for the LLM Guard step."""

    query: str
    chunk_ids: tuple[int, ...]
    chunk_quotes: tuple[str, ...]
    context_correlation_id: Optional[str] = None


@dataclass(frozen=True)
class LLMGuardResult:
    """Typed result carrying the verdict, reason code, and dropped chunks."""

    verdict: GuardrailVerdict
    reason_code: str
    correlation_id: Optional[str]
    affected_chunk_ids: tuple[int, ...] = ()


# Reason codes the M11 guard emits.
REASON_GUARD_ALLOW = "llm_guard_allow"
REASON_GUARD_DOWNGRADE = "llm_guard_downgrade"
REASON_GUARD_REFUSE = "llm_guard_refuse"


__all__ = [
    "GuardrailClassification",
    "GuardrailVerdict",
    "GuardrailInput",
    "GuardrailModelPort",
    "LLMGuardCommand",
    "LLMGuardResult",
    "REASON_GUARD_ALLOW",
    "REASON_GUARD_DOWNGRADE",
    "REASON_GUARD_REFUSE",
]
