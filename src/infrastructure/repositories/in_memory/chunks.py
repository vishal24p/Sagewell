"""
In-memory ChunkRepository.

Active-row lookups only.

M7 adds `replace_for_document` for the ingestion use case. The
implementation is single-event-loop; the chunk id is allocated
atomically. Old active chunks for the document_id retire in the
same call. The whole sequence is in-process; for the Postgres
adapter the same operation runs inside a transaction so a
mid-call failure cannot leave partially active state.
"""
from collections import defaultdict
from datetime import datetime, timezone
from itertools import count
from typing import Iterable, Optional, Sequence

from src.domain.ports.chunks import (
    Chunk,
    ChunkDraft,
    ChunkRepository,
    ChunkReplaceResult,
    ChunkStatus,
)


class InMemoryChunkRepository(ChunkRepository):
    def __init__(self) -> None:
        self._chunks: dict[int, Chunk] = {}
        self._next_id = count(start=1)
        self._clock = lambda: datetime.now(timezone.utc)

    def set_clock(self, clock) -> None:
        """Test seam: provide a deterministic clock."""
        self._clock = clock

    def add(self, chunk: Chunk) -> Chunk:
        self._chunks[chunk.id] = chunk
        return chunk

    async def find_active_by_id(self, chunk_id: int) -> Optional[Chunk]:
        chunk = self._chunks.get(chunk_id)
        if chunk is None or chunk.status != ChunkStatus.ACTIVE:
            return None
        return chunk

    async def find_active_by_ids(self, chunk_ids: Iterable[int]) -> list[Chunk]:
        ids = set(chunk_ids)
        return [
            chunk
            for chunk in self._chunks.values()
            if chunk.id in ids and chunk.status == ChunkStatus.ACTIVE
        ]

    async def find_active_by_document_id(self, document_id: int) -> list[Chunk]:
        return [
            chunk
            for chunk in self._chunks.values()
            if chunk.document_id == document_id and chunk.status == ChunkStatus.ACTIVE
        ]

    async def count_active_by_document_id(self, document_id: int) -> int:
        return sum(
            1
            for chunk in self._chunks.values()
            if chunk.document_id == document_id and chunk.status == ChunkStatus.ACTIVE
        )

    async def replace_for_document(
        self,
        document_id: int,
        drafts: Sequence[ChunkDraft],
    ) -> ChunkReplaceResult:
        # Step 1: retire every active chunk for this document.
        retired_ids: list[int] = []
        now = self._clock()
        for chunk in list(self._chunks.values()):
            if chunk.document_id == document_id and chunk.status == ChunkStatus.ACTIVE:
                retired_ids.append(chunk.id)
                self._chunks[chunk.id] = Chunk(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    ordinal=chunk.ordinal,
                    text=chunk.text,
                    text_search=chunk.text_search,
                    embedding=chunk.embedding,
                    metadata=chunk.metadata,
                    token_count=chunk.token_count,
                    status=ChunkStatus.RETIRED,
                    created_at=chunk.created_at,
                )
        # Step 2: insert the drafts as fresh active rows.
        inserted: list[Chunk] = []
        for draft in drafts:
            new_id = next(self._next_id)
            chunk = Chunk(
                id=new_id,
                document_id=draft.document_id,
                ordinal=draft.ordinal,
                text=draft.text,
                text_search=draft.text_search,
                embedding=draft.embedding,
                metadata=draft.metadata,
                token_count=draft.token_count,
                status=ChunkStatus.ACTIVE,
                created_at=now,
            )
            self._chunks[new_id] = chunk
            inserted.append(chunk)
        return ChunkReplaceResult(
            retired_chunk_ids=tuple(retired_ids),
            inserted_chunks=tuple(inserted),
        )
