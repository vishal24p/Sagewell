"""
V1 RetrievalLog aggregate and RetrievalLogRepository port.

The `candidate_counts` JSON shape is OPEN per KNOWN_ISSUES.md I-007.
The repository stores whatever dict the caller supplies; the
retrieval layer at M8 owns the shape.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol


@dataclass(frozen=True)
class RetrievalLog:
    id: Optional[int]
    actor_user_id: int
    query_text: str
    policy_filter: dict
    retrieval_config: dict
    candidate_counts: dict
    correlation_id: str
    created_at: datetime


class RetrievalLogRepository(Protocol):
    async def append(self, log: RetrievalLog) -> int: ...
