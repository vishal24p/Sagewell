"""Fixtures for the M7 ingestion application use case.

The use case accepts two framework-free protocols:

  - `DocumentChunkerProtocol`
  - `EmbeddingModelProtocol`

Both are stubbed here as deterministic, framework-free fakes.
The stubs let every test exercise the use case in isolation;
the infrastructure-side LlamaIndex adapter (lands at M7's
later step, or as an extension at M8) provides the production-
shaped chunker and embedder.

`deterministic_hash_embedder` produces a deterministic
1536-dim vector from the input text. The vector is reproducible
across calls; the same input yields the same output. Real
production vectors land at M8 when the embedding capability
is wired.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pytest

from src.application.audit_event.dto import RecordAuditCommand
from src.application.audit_event.record import RecordAuditEvent
from src.application.auth.dto import AuthActor
from src.application.ingestion import IngestDocument
from src.domain.ports.audit_logs import AuditDecision, AuditLogRepository
from src.domain.ports.chunks import EMBEDDING_DIM, ChunkRepository
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentRepository
from src.domain.ports.ingestion import (
    ChunkSegment,
    DocumentChunkerProtocol,
    EmbeddingModelProtocol,
)
from src.infrastructure.repositories.in_memory.audit_logs import (
    InMemoryAuditLogRepository,
)
from src.infrastructure.repositories.in_memory.chunks import (
    InMemoryChunkRepository,
)
from src.infrastructure.repositories.in_memory.documents import (
    InMemoryDocumentRepository,
)


class FixedSizeChunker(DocumentChunkerProtocol):
    """Deterministic, tokenizer-free chunker.

    Splits at every N characters (defaults to 16). Useful for
    unit tests — no semantic splitter, no LlamaIndex, no
    network. The chunk text is the raw substring; metadata
    carries the ordinal and chunk-length for observability
    rows.
    """

    def __init__(self, chunk_size: int = 16) -> None:
        self._chunk_size = chunk_size

    def chunk(self, text: str) -> Sequence[ChunkSegment]:
        size = self._chunk_size
        if size <= 0:
            return [
                ChunkSegment(ordinal=0, text=text, metadata={})
            ]
        segments: list[ChunkSegment] = []
        ordinal = 0
        cursor = 0
        length = len(text)
        while cursor < length:
            segment_text = text[cursor : cursor + size]
            # Skip pure-whitespace chunks (they would land as
            # empty embedding inputs).
            if segment_text.strip():
                segments.append(
                    ChunkSegment(
                        ordinal=ordinal,
                        text=segment_text,
                        metadata={
                            "ordinal": ordinal,
                            "length": len(segment_text),
                        },
                    )
                )
                ordinal += 1
            cursor += size
        return segments


class DeterministicHashEmbedder(EmbeddingModelProtocol):
    """Embed text into a fixed-size deterministic vector.

    Uses a position-by-position hash so the same input text
    yields the same `list[float]` of length `EMBEDDING_DIM`.
    Production-grade embeddings land at M8 via a
    capability-based remote client; this stub is a
    reproduction-safe test embedder only.
    """

    def embed(self, text: str) -> list[float]:
        # Seed a stable per-ordinal pseudo-random walk deterministically.
        # Each dimension draws from sha256(text + ":dim-N").
        import hashlib

        vector: list[float] = []
        for dim in range(EMBEDDING_DIM):
            digest = hashlib.sha256(
                f"{text}|dim-{dim}".encode("utf-8")
            ).digest()
            # Use the first 4 bytes as a tiny int modulo 1000 -> [-1, 1].
            raw = int.from_bytes(digest[:4], "big") % 1000
            vector.append((raw / 500.0) - 1.0)
        return vector


@pytest.fixture
def actor() -> AuthActor:
    return AuthActor(
        user_id="u-m7-ingestion",
        department="engineering",
        clearance="internal",
        role="contributor",
        correlation_id="corr-m7-ingestion",
    )


@pytest.fixture
def document_repo() -> DocumentRepository:
    return InMemoryDocumentRepository()


@pytest.fixture
def chunk_repo() -> ChunkRepository:
    return InMemoryChunkRepository()


@pytest.fixture
def audit_repo() -> AuditLogRepository:
    return InMemoryAuditLogRepository()


@dataclass
class _FrozenClock:
    """Frozen clock for deterministic created_at values."""

    iso_format: str = "2026-06-25T00:00:00+00:00"

    def now(self):
        from datetime import datetime, timezone

        return datetime.fromisoformat(self.iso_format)


@pytest.fixture
def clock():
    return _FrozenClock()


@pytest.fixture
def record_audit_event(audit_repo, clock):
    return RecordAuditEvent(audit_repo, clock=clock)


@pytest.fixture
def chunker() -> DocumentChunkerProtocol:
    return FixedSizeChunker(chunk_size=8)


@pytest.fixture
def embedder() -> EmbeddingModelProtocol:
    return DeterministicHashEmbedder()


@pytest.fixture
def use_case(
    document_repo,
    chunk_repo,
    chunker,
    embedder,
    record_audit_event,
):
    return IngestDocument(
        documents=document_repo,
        chunks=chunk_repo,
        chunker=chunker,
        embedder=embedder,
        record_audit_event=record_audit_event,
        clearance_enum=Clearance,
    )


@pytest.fixture
def make_cmd(actor):
    """Factory for `IngestDocumentCommand` with sensible defaults."""

    def _make(**overrides):
        defaults = {
            "actor": actor,
            "source_system": "fixture",
            "source_id": "doc-001",
            "title": "Test Doc",
            "uri": None,
            "department": "engineering",
            "required_clearance": Clearance.INTERNAL,
            "content": (
                "First chunk. Second chunk. Third chunk. Fourth chunk."
            ),
            "metadata": {},
            "correlation_id": "corr-m7-test",
        }
        defaults.update(overrides)
        from src.application.ingestion.ingest import (
            IngestDocumentCommand,
        )

        return IngestDocumentCommand(**defaults)

    return _make
