"""
Parity tests for ChunkRepository.

Embedding is exercised against the Postgres backend only because
the in-memory adapter stores the literal list and does not
validate dimension by default. Both backends guarantee the row
round-trips; the dimension constant is shared (EMBEDDING_DIM).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytest

from src.domain.ports.chunks import EMBEDDING_DIM, Chunk, ChunkStatus


def _chunk_row(
    id: int = 1,
    *,
    status: str = "active",
    embedding: Optional[list[float]] = None,
) -> dict:
    return {
        "id": id,
        "document_id": 42,
        "ordinal": id,
        "text": f"text {id}",
        "text_search": f"text {id}",
        "embedding": embedding,
        "metadata": {"source": "fixture"},
        "token_count": 4,
        "status": status,
        "created_at": datetime(2026, 6, 19, tzinfo=timezone.utc),
    }


async def _seed_chunk(repo, raw: dict, pool=None) -> None:
    if pool is None:
        repo.add(
            Chunk(
                id=raw["id"],
                document_id=raw["document_id"],
                ordinal=raw["ordinal"],
                text=raw["text"],
                text_search=raw["text_search"],
                embedding=raw["embedding"],
                metadata=raw["metadata"] or {},
                token_count=raw["token_count"],
                status=ChunkStatus(raw["status"]),
                created_at=raw["created_at"],
            )
        )
    else:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chunks (
                  id, document_id, ordinal, text, text_search,
                  embedding, metadata, token_count, status, created_at
                ) VALUES (
                  $1,$2,$3,$4,$5,$6::vector,$7::jsonb,$8,$9,$10
                )
                """,
                raw["id"],
                raw["document_id"],
                raw["ordinal"],
                raw["text"],
                raw["text_search"],
                raw["embedding"],
                raw["metadata"] or {},
                raw["token_count"],
                raw["status"],
                raw["created_at"],
            )


class TestChunkRepository:
    @pytest.fixture
    async def setup(self, adapter, seed_parent_rows):
        backend, factory, pool = adapter
        _user, _doc, chunk_repo, *_ = factory(pool)
        # Two active rows and one retired row for filter testing.
        await _seed_chunk(chunk_repo, _chunk_row(1), pool)
        await _seed_chunk(chunk_repo, _chunk_row(2), pool)
        await _seed_chunk(chunk_repo, _chunk_row(3, status="retired"), pool)
        return backend, chunk_repo, pool

    async def test_find_active_by_id(self, setup):
        _backend, repo, _pool = setup
        chunk = await repo.find_active_by_id(1)
        assert chunk is not None
        assert chunk.id == 1

    async def test_find_active_by_id_excludes_retired(self, setup):
        _backend, repo, _pool = setup
        assert await repo.find_active_by_id(3) is None

    async def test_find_active_by_ids_excludes_retired(self, setup):
        _backend, repo, _pool = setup
        chunks = await repo.find_active_by_ids([1, 2, 3])
        ids = sorted(c.id for c in chunks)
        assert ids == [1, 2]

    async def test_find_active_by_document_id(self, setup):
        _backend, repo, _pool = setup
        chunks = await repo.find_active_by_document_id(42)
        ids = sorted(c.id for c in chunks)
        assert ids == [1, 2]

    async def test_count_active_by_document_id(self, setup):
        _backend, repo, _pool = setup
        assert await repo.count_active_by_document_id(42) == 2


class TestChunkRepositoryEmbeddingDimContract:
    """Postgres-backed test asserts the embedding dimension contract."""

    @pytest.fixture
    async def setup_embedding(self, adapter, seed_parent_rows):
        backend, _factory, pool = adapter
        if pool is None:
            pytest.skip("embedding dimension test requires the Postgres backend")
        _user, _doc, chunk_repo, *_ = _factory(pool)
        full_vec = [0.01] * EMBEDDING_DIM  # pgvector round-trip
        await _seed_chunk(chunk_repo, _chunk_row(10, embedding=full_vec), pool)
        return chunk_repo

    async def test_full_embedding_round_trips(self, setup_embedding):
        repo = setup_embedding
        chunk = await repo.find_active_by_id(10)
        assert chunk is not None
        assert chunk.embedding is not None
        assert len(chunk.embedding) == EMBEDDING_DIM
