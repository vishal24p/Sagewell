"""M13 -- RAGAS evaluation use case.

The `RunRagasCase` use case takes a `RagasCase`
(defined in `src/domain/ports/ragas.py`), invokes
the configured `RagasScorerPort`, and returns a
`RagasVerdict`. The verdicts may be persisted via
M12's `RecordRetrievalLog` / `RecordGuardVerdict`
adapters (or directly through the
`EvaluationResultRepository`) at the workflow
boundary.

The use case is async. The model port is injected;
production wiring uses the hosted-RAGAS SDK (open
question D-006 owns the adoption milestone); tests
inject a stub scorer.

The scoring contract:

  - Every metric in `case.minimums` (when set)
    must be at or above its threshold.
  - Metrics absent from `minimums` are
    informational only.
  - The verdict is `passed` iff the threshold
    rule holds for every declared metric.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.domain.ports.ragas import (
    RagasCase,
    RagasScore,
    RagasScorerPort,
    RagasVerdict,
)


__all__ = ["RunRagasCase", "RunRagasCaseCommand"]


@dataclass(frozen=True)
class RunRagasCaseCommand:
    """Typed command."""

    case: RagasCase


class RunRagasCase:
    """M13 RAGAS run use case."""

    def __init__(self, *, scorer: RagasScorerPort) -> None:
        self._scorer = scorer

    async def execute(self, command: RunRagasCaseCommand) -> RagasVerdict:
        case = command.case
        score: RagasScore = await self._scorer.score(case)
        failures: list[str] = []
        for metric, threshold in case.minimums.items():
            observed = score.metrics.get(metric)
            if observed is None:
                failures.append(
                    f"missing metric {metric.value} scorer output"
                )
                continue
            if observed + 1e-9 < float(threshold):
                failures.append(
                    f"metric {metric.value}: observed {observed:.4f} "
                    f"< threshold {float(threshold):.4f}"
                )
        passed = not failures
        return RagasVerdict(
            case_key=case.case_key,
            passed=passed,
            scores=score,
            failure_reason=(
                "; ".join(failures) if failures else None
            ),
        )
