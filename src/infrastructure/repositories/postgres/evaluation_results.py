"""
Postgres-backed EvaluationResultRepository.

Validates suite enum at the application boundary.
"""
from __future__ import annotations

import asyncpg

from src.domain.ports.errors import PersistenceError
from src.domain.ports.evaluation_results import (
    EvaluationResult,
    EvaluationResultRepository,
    EvaluationStatus,
    Suite,
)


_STATUS_BY_TEXT = {
    "passed": EvaluationStatus.PASSED,
    "failed": EvaluationStatus.FAILED,
    "skipped": EvaluationStatus.SKIPPED,
}


def _coerce_result(row: asyncpg.Record) -> EvaluationResult:
    status_text = row["status"]
    status = _STATUS_BY_TEXT.get(status_text)
    if status is None:
        raise PersistenceError(
            f"evaluation_results.status is not V1: {status_text!r}"
        )
    return EvaluationResult(
        id=row["id"],
        suite=Suite(row["suite"]),
        case_key=row["case_key"],
        input=row["input"] or {},
        expected=row["expected"] or {},
        status=status,
        scores=row["scores"] or {},
        failure_reason=row["failure_reason"],
        model_config=row["model_config"] or {},
        created_at=row["created_at"],
    )


class PostgresEvaluationResultRepository(EvaluationResultRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record(self, result: EvaluationResult) -> int:
        # Reject raw strings and unknown enum values uniformly.
        # Postgres adapter coerces at the read layer; runtime
        # inserts arrive as `Suite`, raw strings, or bad members.
        # All but valid `Suite` instances must raise PersistenceError.
        if not isinstance(result.suite, Suite) or (
            isinstance(result.suite, Suite) and result.suite.value
            not in {member.value for member in Suite}
        ):
            raise PersistenceError(
                f"suite not in {{ragas, rbac_access_outcome}}: {result.suite!r}"
            )
        async with self._pool.acquire() as conn:
            new_id = await conn.fetchval(
                "INSERT INTO evaluation_results ("
                "  suite, case_key, input, expected, status, scores,"
                "  failure_reason, model_config, created_at"
                ") VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6::jsonb, $7, $8::jsonb, $9) "
                "RETURNING id",
                result.suite.value,
                result.case_key,
                result.input,
                result.expected,
                result.status.value,
                result.scores,
                result.failure_reason,
                result.model_config,
                result.created_at,
            )
        if new_id is None:
            raise PersistenceError("evaluation_results INSERT returned no id")
        return int(new_id)

    async def list_by_suite(self, suite: Suite) -> list[EvaluationResult]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM evaluation_results WHERE suite = $1 "
                "ORDER BY id ASC",
                suite.value,
            )
        return [_coerce_result(row) for row in rows]
