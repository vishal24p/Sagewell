"""
V1 ingestion ports.

These two protocols are what M7 needs beyond the existing
documents / chunks repository ports:

- `DocumentChunkerProtocol`: split a document's text into
  chunk-sized units, preserving ordinal order and metadata.
- `EmbeddingModelProtocol`: turn a normalized chunk text into
  a fixed-length dense vector.

Both protocols are deliberately framework-free:

- The application layer imports them only as protocols; the
  concrete LlamaIndex, sentence-transformers, or other
  implementations live under `src/infrastructure/`.
- The protocols emit **capability-shaped** values: a chunk list
  with ordinal + metadata and an embedding of length
  `EMBEDDING_DIM`. No specific vectorizer, no specific
  dimensionality assumption beyond the `EMBEDDING_DIM`
  constant already locked at M1.
- Neither protocol is async-IO-aware: the implementations may be
  async if needed (the embedder may batch-load remote models);
  the application use-case awaits the implementation's
  callable result.

The application use case `IngestDocument` accepts both
protocols as constructor dependencies. The infrastructure
adapter wires a single LlamaIndex-backed chunker + a
capability-based embedding model; tests wire a deterministic
hash-based chunker + a hash-based embedder.
"""
from dataclasses import dataclass, field
from typing import Protocol, Sequence

from .chunks import EMBEDDING_DIM


@dataclass(frozen=True)
class ChunkSegment:
    """A unit that the chunker emits.

    `ordinal` is the chunk's order within the supplied
    document. `text` is the normalized chunk text. `metadata`
    is free-form JSON-friendly information the chunker
    attaches (ex: section title, page hints).
    """
    ordinal: int
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk:
    """The M7 ingestion application-level chunk payload.

    The chunker returns a sequence of `ChunkSegment`s; the
    application use case converts each `ChunkSegment` to a
    `DocumentChunk` after assigning the document's canonical
    id and after embedding the text through the embedding
    model.
    """
    document_id: int
    ordinal: int
    text: str
    embedding: list[float]
    metadata: dict = field(default_factory=dict)
    token_count: int | None = None
    text_search: str | None = None


class DocumentChunkerProtocol(Protocol):
    """Application-side chunking boundary.

    Implementations:

    - `src/infrastructure/ingestion/llama_index_chunker.LlamaIndexChunker`
      — wraps LlamaIndex's text splitters (semantic chunking
      and SentenceSplitter as available).
    - `tests/application/ingestion/conftest.py` — a fixed-size
      tokenizer-free chunker for unit tests.

    The chunker is responsible for splitting; the embedder is
    responsible for vectorization. The two are independent
    boundaries so the embedder can be substituted or mocked.
    """

    def chunk(self, text: str) -> Sequence[ChunkSegment]: ...


class EmbeddingModelProtocol(Protocol):
    """Application-side embedding boundary.

    Capability-based. The Embedding Model parameter shape lives
    at the implementation layer; this protocol emits only the
    canonical `list[float]` of length `EMBEDDING_DIM`.

    Implementations:

    - `src/infrastructure/ingestion/embedding_adapter.PgvectorEmbeddingModel`
      — uses the pgvector codec and a capability-based remote
      client (the actual SDK is owned by a future M8 / M11
      adapter; M7 ships a deterministic hash-based stub).
    """

    def embed(self, text: str) -> list[float]: ...


__all__ = [
    "ChunkSegment",
    "DocumentChunk",
    "DocumentChunkerProtocol",
    "EmbeddingModelProtocol",
    "EMBEDDING_DIM",
]
