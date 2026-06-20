"""
In-memory RetrievalLogRepository.

Stores candidate_counts as the dict the caller supplies; shape is
not constrained (KNOWN_ISSUES.md I-007).
"""
from src.domain.ports.errors import PersistenceError
from src.domain.ports.retrieval_logs import RetrievalLog, RetrievalLogRepository


class InMemoryRetrievalLogRepository(RetrievalLogRepository):
    def __init__(self) -> None:
        self._logs: list[RetrievalLog] = []
        self._next_id: int = 1

    async def append(self, log: RetrievalLog) -> int:
        if log.actor_user_id <= 0:
            raise PersistenceError("retrieval_log requires positive actor_user_id")
        if not log.correlation_id:
            raise PersistenceError("retrieval_log requires correlation_id")
        new_id = self._next_id
        self._next_id += 1
        materialized = RetrievalLog(
            id=new_id,
            actor_user_id=log.actor_user_id,
            query_text=log.query_text,
            policy_filter=log.policy_filter,
            retrieval_config=log.retrieval_config,
            candidate_counts=log.candidate_counts,
            correlation_id=log.correlation_id,
            created_at=log.created_at,
        )
        self._logs.append(materialized)
        return new_id
