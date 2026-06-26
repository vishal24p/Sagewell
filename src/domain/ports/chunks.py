"""
V1 Chunk aggregate and ChunkRepository port.

Scope is intentionally narrow: ChunkRepository answers active-row
lookups by id and by document_id only. BM25 / dense / HNSW
similarity queries live in M8 retrieval adapters, not in the
repository tier.

`embedding` is `list[float] | None` (1536-dim per ADR-0004; NULL
for fixture rows). Marshalling with the pgvector wire format is
handled by the Postgres adapter's codec registration.

M7 adds `replace_for_document` for the ingestion use case. The
method retires every active chunk for the supplied document_id
and inserts the supplied sequence of fresh chunks. Inserted
chunks are returned with their canonical ids so the application
can attach them to retrieval_logs / candidates later.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable, Optional, Protocol, Sequence


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


@dataclass(frozen=True)
class ChunkDraft:
    """The application-supplied chunk payload for M7 ingestion.

    The repository assigns id / created_at on insert. `embedding`
    is `list[float]` of length `EMBEDDING_DIM`; the application
    raises `ValueError` if the embedder returns a different
    shape.
    """
    document_id: int
    ordinal: int
    text: str
    text_search: Optional[str]
    embedding: list[float]
    metadata: dict
    token_count: Optional[int]


@dataclass(frozen=True)
class ChunkReplaceResult:
    """Outcome of `replace_for_document`.

    - `retired_chunk_ids`: ids of the previously-active chunks
      marked `retired` in this call.
    - `inserted_chunks`: the freshly-inserted Chunk rows
      (with canonical ids + created_at).
    """
    retired_chunk_ids: tuple[int, ...]
    inserted_chunks: tuple[Chunk, ...]


class ChunkRepository(Protocol):
    async def find_active_by_id(self, chunk_id: int) -> Optional[Chunk]: ...

    async def find_active_by_ids(self, chunk_ids: Iterable[int]) -> list[Chunk]: ...

    async def find_active_by_document_id(self, document_id: int) -> list[Chunk]: ...

    async def count_active_by_document_id(self, document_id: int) -> int: ...

    async def replace_for_document(
        self,
        document_id: int,
        drafts: Sequence[ChunkDraft],
    ) -> ChunkReplaceResult: ...
