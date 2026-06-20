"""
Postgres-backed RetrievalLogRepository.

Stores candidate_counts as a dict. Shape is OPEN per
KNOWN_ISSUES.md I-007.
"""
from __future__ import annotations

import asyncpg

from src.domain.ports.errors import PersistenceError
from src.domain.ports.retrieval_logs import RetrievalLog, RetrievalLogRepository


class PostgresRetrievalLogRepository(RetrievalLogRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def append(self, log: RetrievalLog) -> int:
        if log.actor_user_id is None or log.actor_user_id <= 0:
            raise PersistenceError("retrieval_log requires positive actor_user_id")
        if not log.correlation_id:
            raise PersistenceError("retrieval_log requires correlation_id")
        async with self._pool.acquire() as conn:
            new_id = await conn.fetchval(
                "INSERT INTO retrieval_logs ("
                "  actor_user_id, query_text, policy_filter, retrieval_config,"
                "  candidate_counts, correlation_id, created_at"
                ") VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6, $7) "
                "RETURNING id",
                log.actor_user_id,
                log.query_text,
                log.policy_filter,
                log.retrieval_config,
                log.candidate_counts,
                log.correlation_id,
                log.created_at,
            )
        if new_id is None:
            raise PersistenceError("retrieval_logs INSERT returned no id")
        return int(new_id)
