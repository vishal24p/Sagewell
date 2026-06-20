"""
Parity tests for RetrievalLogRepository.

candidate_counts is a free-form dict per KNOWN_ISSUES.md I-007.
The repository only validates required inputs.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.domain.ports.errors import PersistenceError
from src.domain.ports.retrieval_logs import RetrievalLog


def _log() -> RetrievalLog:
    return RetrievalLog(
        id=None,
        actor_user_id=1,
        query_text="redacted",
        policy_filter={"decision": "denied"},
        retrieval_config={"top_k": 50},
        candidate_counts={"dense": 50, "bm25": 50, "fused": 50, "reranked": 10, "after_access": 8},
        correlation_id="corr-1",
        created_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
    )


class TestRetrievalLogRepository:
    @pytest.fixture
    async def log_repo(self, adapter, seed_parent_rows):
        backend, factory, pool = adapter
        _user, _doc, _chunk, _audit, log, _eval = factory(pool)
        return log

    async def test_append_assigns_id(self, log_repo):
        new_id = await log_repo.append(_log())
        assert new_id > 0

    async def test_append_rejects_nonpositive_actor_user_id(self, log_repo):
        log = _log()
        bad = RetrievalLog(
            id=None,
            actor_user_id=0,
            query_text=log.query_text,
            policy_filter=log.policy_filter,
            retrieval_config=log.retrieval_config,
            candidate_counts=log.candidate_counts,
            correlation_id=log.correlation_id,
            created_at=log.created_at,
        )
        with pytest.raises(PersistenceError):
            await log_repo.append(bad)

    async def test_append_rejects_empty_correlation_id(self, log_repo):
        log = _log()
        bad = RetrievalLog(
            id=None,
            actor_user_id=log.actor_user_id,
            query_text=log.query_text,
            policy_filter=log.policy_filter,
            retrieval_config=log.retrieval_config,
            candidate_counts=log.candidate_counts,
            correlation_id="",
            created_at=log.created_at,
        )
        with pytest.raises(PersistenceError):
            await log_repo.append(bad)
