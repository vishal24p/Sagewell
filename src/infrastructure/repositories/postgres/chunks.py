"""
Postgres-backed ChunkRepository.

Active-row lookups only. BM25 / dense similarity lives in M8.
The pgvector codec is registered by the pool's init callback, so
the `embedding` column round-trips as `list[float] | None`.

M7 adds `replace_for_document` for the ingestion use case. The
implementation runs inside a single transaction so a mid-call
failure cannot leave partially active rows: every previously-
active chunk for the document_id retires with a single UPDATE
statement, the fresh rows insert with one parameterized
multi-row INSERT, and Postgres guarantees either both happen
or neither does.
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence

import asyncpg

from src.domain.ports.chunks import (
    Chunk,
    ChunkDraft,
    ChunkRepository,
    ChunkReplaceResult,
    ChunkStatus,
)
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

    async def replace_for_document(
        self,
        document_id: int,
        drafts: Sequence[ChunkDraft],
    ) -> ChunkReplaceResult:
        retired_ids: list[int] = []
        inserted_chunks: list[Chunk] = []
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Step 1: retire every active chunk for this
                # document. The retired row id list lets the caller
                # emit observability rows (M12 will reuse this).
                retired_rows = await conn.fetch(
                    "UPDATE chunks SET status = 'retired' "
                    "WHERE document_id = $1 AND status = 'active' "
                    "RETURNING id",
                    document_id,
                )
                retired_ids = [row["id"] for row in retired_rows]
                # Step 2: insert fresh active chunks via a single
                # multi-row INSERT using UNNEST on the typed columns.
                # The pgvector asyncpg codec handles the `embedding`
                # parameter as `vector`; we hand the list[float]
                # straight through.
                if not drafts:
                    return ChunkReplaceResult(
                        retired_chunk_ids=tuple(retired_ids),
                        inserted_chunks=tuple(),
                    )
                doc_ids = [draft.document_id for draft in drafts]
                ordinals = [draft.ordinal for draft in drafts]
                texts = [draft.text for draft in drafts]
                text_searches = [draft.text_search for draft in drafts]
                embeddings = [draft.embedding for draft in drafts]
                metadatas = [
                    (draft.metadata if draft.metadata else {})
                    for draft in drafts
                ]
                token_counts = [draft.token_count for draft in drafts]
                inserted = await conn.fetch(
                    "INSERT INTO chunks ("
                    "  document_id, ordinal, text, text_search,"
                    "  embedding, metadata, token_count, status"
                    ") "
                    "SELECT * FROM UNNEST("
                    "  $1::bigint[], $2::int[], $3::text[],"
                    "  $4::text[], $5::vector[],"
                    "  $6::jsonb[], $7::int[]"
                    ") AS t("
                    "  document_id, ordinal, text, text_search,"
                    "  embedding, metadata, token_count"
                    ") "
                    "RETURNING *",
                    doc_ids,
                    ordinals,
                    texts,
                    text_searches,
                    embeddings,
                    metadatas,
                    token_counts,
                )
                for row in inserted:
                    inserted_chunks.append(_coerce_chunk(row))
        inserted_chunks.sort(key=lambda c: c.ordinal)
        return ChunkReplaceResult(
            retired_chunk_ids=tuple(retired_ids),
            inserted_chunks=tuple(inserted_chunks),
        )
