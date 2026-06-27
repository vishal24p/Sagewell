"""M13 -- RAGAS evaluation domain ports.

The RAGAS suite at V1 is shipped as the typed
contract + a capability-shaped scorer port. The
RAGAS SDK is intentionally NOT pinned; the
adoption milestone owns the SDK selection. The
V1 surface here is:

  - `RagasMetric`: the four V1 metrics (Faithfulness,
    Context Precision, Context Recall, Answer Relevancy).
  - `RagasCase`: the canonical V1 case shape (query,
    answer, retrieved contexts, ground truth contexts +
    answer, expected metric minimums).
  - `RagasScorerPort`: capability-shaped scorer
    (Open question D-006 owns the SDK adoption).
  - `RagasScore`: canonical per-metric score object
    (0..1 floats per metric).

The application package imports the ports only; the
production RAGAS SDK adoption lands at the milestone
that owns open question D-006.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional, Protocol, Sequence


class RagasMetric(str, Enum):
    FAITHFULNESS = "faithfulness"
    CONTEXT_PRECISION = "context_precision"
    CONTEXT_RECALL = "context_recall"
    ANSWER_RELEVANCY = "answer_relevancy"


@dataclass(frozen=True)
class RagasCase:
    """The canonical V1 RAGAS case shape.

    - `case_key`: stable slug, e.g. `faq_001` or
      `incident_response_017`.
    - `query`: the user-side test query.
    - `answer`: the V1 answer the system produced
      (or empty when evaluating the allow-empty case).
    - `retrieved_contexts`: the chunk quotes the
      M9 verifier / M8 orchestrator surfaced (a
      subset of `VerifyCitationsResult.allowed_citations`).
    - `ground_truth_contexts`: the canonical
      gold-context set the V1 dataset carries.
    - `ground_truth_answer`: the canonical gold
      answer for Answer Relevancy.
    - `minimums`: optional map of `RagasMetric ->
      threshold` that the case insists on
      (used for `RAGAS_FAIL_THRESHOLD` open-question D-006).
    """

    case_key: str
    query: str
    answer: str
    retrieved_contexts: tuple[str, ...]
    ground_truth_contexts: tuple[str, ...]
    ground_truth_answer: str
    minimums: Mapping[RagasMetric, float] = ()


@dataclass(frozen=True)
class RagasScore:
    """Per-metric scores in the canonical 0..1 range.

    `metrics` maps `RagasMetric` to the score.
    `rationale` is required so the audit row carries
    an explainable result. The four V1 metrics are
    the allowed keyset -- other keys are rejected
    by the scorer port.
    """

    metrics: Mapping[RagasMetric, float]
    rationale: str = ""


class RagasScorerPort(Protocol):
    """The RAGAS SDK capability port.

    `score(case)` returns a `RagasScore`. The
    production SDK adoption lands at the milestone
    that owns open question D-006.
    """

    async def score(self, case: RagasCase) -> RagasScore: ...


@dataclass(frozen=True)
class RagasVerdict:
    """The M13 use case verdict.

    - `case_key`: echoes the input.
    - `passed`: True iff every metric in
      `case.minimums` (when set) is at or above
      its threshold; metrics absent from
      `minimums` are informational.
    - `scores`: the typed `RagasScore`.
    - `failure_reason`: human-readable summary
      when `passed=False`.
    """

    case_key: str
    passed: bool
    scores: RagasScore
    failure_reason: Optional[str]


__all__ = [
    "RagasMetric",
    "RagasCase",
    "RagasScore",
    "RagasScorerPort",
    "RagasVerdict",
]
