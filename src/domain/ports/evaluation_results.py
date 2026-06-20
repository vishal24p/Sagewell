"""
V1 EvaluationResult aggregate and EvaluationResultRepository port.

`suite` is one of `'ragas' | 'rbac_access_outcome'`. The
repository validates the value at the application boundary.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Protocol


class Suite(str, Enum):
    RAGAS = "ragas"
    RBAC_ACCESS_OUTCOME = "rbac_access_outcome"


class EvaluationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class EvaluationResult:
    id: Optional[int]
    suite: Suite
    case_key: str
    input: dict
    expected: dict
    status: EvaluationStatus
    scores: dict
    failure_reason: Optional[str]
    model_config: dict
    created_at: datetime


class EvaluationResultRepository(Protocol):
    async def record(self, result: EvaluationResult) -> int: ...

    async def list_by_suite(self, suite: Suite) -> list[EvaluationResult]: ...
