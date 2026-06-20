"""
In-memory ChunkRepository.

Active-row lookups only.
"""
from collections import defaultdict
from typing import Iterable, Optional

from src.domain.ports.chunks import Chunk, ChunkRepository, ChunkStatus


class InMemoryChunkRepository(ChunkRepository):
    def __init__(self) -> None:
        self._chunks: dict[int, Chunk] = {}

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
