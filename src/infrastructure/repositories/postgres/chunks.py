"""
Postgres-backed ChunkRepository.

Active-row lookups only. BM25 / dense similarity lives in M8.
The pgvector codec is registered by the pool's init callback, so
the `embedding` column round-trips as `list[float] | None`.
"""
from __future__ import annotations

from typing import Iterable, Optional

import asyncpg

from src.domain.ports.chunks import Chunk, ChunkRepository, ChunkStatus
from src.domain.ports.errors import PersistenceError


def _coerce_chunk(row: asyncpg.Record) -> Chunk:
    try:
        status = ChunkStatus(row["status"])
    except ValueError as exc:
        raise PersistenceError(
            f"chunks.status is not a V1 status: {row['status']!r}"
        ) from exc
    return Chunk(
        id=row["id"],
        document_id=row["document_id"],
        ordinal=row["ordinal"],
        text=row["text"],
        text_search=row["text_search"],
        embedding=row["embedding"],
        metadata=row["metadata"] or {},
        token_count=row["token_count"],
        status=status,
        created_at=row["created_at"],
    )


class PostgresChunkRepository(ChunkRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_active_by_id(self, chunk_id: int) -> Optional[Chunk]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM chunks WHERE id = $1 AND status = 'active'",
                chunk_id,
            )
        return _coerce_chunk(row) if row is not None else None

    async def find_active_by_ids(self, chunk_ids: Iterable[int]) -> list[Chunk]:
        ids = list(chunk_ids)
        if not ids:
            return []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM chunks WHERE id = ANY($1::bigint[]) "
                "AND status = 'active'",
                ids,
            )
        return [_coerce_chunk(row) for row in rows]

    async def find_active_by_document_id(self, document_id: int) -> list[Chunk]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM chunks WHERE document_id = $1 "
                "AND status = 'active' "
                "ORDER BY ordinal ASC",
                document_id,
            )
        return [_coerce_chunk(row) for row in rows]

    async def count_active_by_document_id(self, document_id: int) -> int:
        async with self._pool.acquire() as conn:
            value = await conn.fetchval(
                "SELECT count(*) FROM chunks "
                "WHERE document_id = $1 AND status = 'active'",
                document_id,
            )
        return int(value or 0)
