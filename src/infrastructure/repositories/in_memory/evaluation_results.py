"""
In-memory EvaluationResultRepository.

Validates suite is one of the V1 allowed values.
"""
from src.domain.ports.errors import PersistenceError
from src.domain.ports.evaluation_results import (
    EvaluationResult,
    EvaluationResultRepository,
    Suite,
)


class InMemoryEvaluationResultRepository(EvaluationResultRepository):
    def __init__(self) -> None:
        self._results: list[EvaluationResult] = []
        self._next_id: int = 1

    async def record(self, result: EvaluationResult) -> int:
        # Mirror the postgres adapter's runtime guard: reject raw
        # strings uniformly; only valid Suite instances pass.
        if (
            not isinstance(result.suite, Suite)
            or result.suite.value
            not in {member.value for member in Suite}
        ):
            raise PersistenceError(
                f"suite not in {{ragas, rbac_access_outcome}}: {result.suite!r}"
            )
        new_id = self._next_id
        self._next_id += 1
        materialized = EvaluationResult(
            id=new_id,
            suite=result.suite,
            case_key=result.case_key,
            input=result.input,
            expected=result.expected,
            status=result.status,
            scores=result.scores,
            failure_reason=result.failure_reason,
            model_config=result.model_config,
            created_at=result.created_at,
        )
        self._results.append(materialized)
        return new_id

    async def list_by_suite(self, suite: Suite) -> list[EvaluationResult]:
        return [r for r in self._results if r.suite == suite]
