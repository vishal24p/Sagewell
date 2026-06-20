"""
V1 Chunk aggregate and ChunkRepository port.

Scope is intentionally narrow: ChunkRepository answers active-row
lookups by id and by document_id only. BM25 / dense / HNSW
similarity queries live in M8 retrieval adapters, not in the
repository tier.

`embedding` is `list[float] | None` (1536-dim per ADR-0004; NULL
for fixture rows). Marshalling with the pgvector wire format is
handled by the Postgres adapter's codec registration.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable, Optional, Protocol


class ChunkStatus(str, Enum):
    ACTIVE = "active"
    RETIRED = "retired"


# Stable per ADR-0004: chunks.embedding is vector(1536).
EMBEDDING_DIM = 1536


@dataclass(frozen=True)
class Chunk:
    id: int
    document_id: int
    ordinal: int
    text: str
    text_search: Optional[str]
    embedding: Optional[list[float]]
    metadata: dict
    token_count: Optional[int]
    status: ChunkStatus
    created_at: datetime


class ChunkRepository(Protocol):
    async def find_active_by_id(self, chunk_id: int) -> Optional[Chunk]: ...

    async def find_active_by_ids(self, chunk_ids: Iterable[int]) -> list[Chunk]: ...

    async def find_active_by_document_id(self, document_id: int) -> list[Chunk]: ...

    async def count_active_by_document_id(self, document_id: int) -> int: ...
