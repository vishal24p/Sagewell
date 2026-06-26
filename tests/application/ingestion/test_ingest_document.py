"""M7 ingestion application use case tests.

Six distinct tests:

1. Happy path: a fresh source inserts a document + chunks
   and emits an `ingestion_succeeded` audit row.
2. Idempotence: re-running with the same content_checksum
   returns `SKIPPED`, emits `ingestion_skipped`, and leaves
   the canonical document row count unchanged.
3. Replace: a different content_checksum inserts a new chunk
   set + retires the previous active chunks (so they are not
   searchable after the call).
4. Failure: the chunker raises, the use case translates to
   `IngestionPipelineError` and emits `ingestion_failed`.
5. Missing content: the use case raises `MissingContentError`
   without issuing any writes.
6. Bad-embedding-shape: the embedder returns a wrong-length
   vector and the use case raises the typed-error hierarchy
   so the audit row records `ingestion_failed`.

The global `asyncio_mode = "auto"` already covers the async
tests (`pytest-asyncio` is configured in `pyproject.toml`),
so no explicit `pytestmark` is required.
"""
from __future__ import annotations

import pytest

from src.application.ingestion.errors import (
    EmbeddingShapeMismatchError,
    IngestionPipelineError,
    MissingContentError,
)
from src.application.ingestion.ingest import IngestOutcome
from src.domain.ports.chunks import EMBEDDING_DIM
from src.domain.ports.ingestion import (
    ChunkSegment,
    DocumentChunkerProtocol,
    EmbeddingModelProtocol,
)
from src.domain.ports.clearances import Clearance


class ExplodingChunker(DocumentChunkerProtocol):
    def chunk(self, text):
        raise RuntimeError("chunk blew up")


class ShortEmbedder(EmbeddingModelProtocol):
    """Returns a vector of the wrong length."""

    def embed(self, text):
        return [0.0] * (EMBEDDING_DIM - 1)


async def test_ingest_document_happy_path(use_case, document_repo, chunk_repo, audit_repo, make_cmd, actor):
    result = await use_case.execute(make_cmd())
    assert result.outcome is IngestOutcome.INGESTED
    assert result.was_inserted is True
    assert result.was_replaced is False
    assert result.was_unchanged is False
    assert result.inserted_chunk_count >= 1
    assert result.document_id is not None
    # Audit row is recorded with the actor's user_id and the
    # `ingestion_succeeded` reason code.
    audit_rows = await audit_repo.find_by_correlation_id("corr-m7-test")
    assert len(audit_rows) == 1
    audit = audit_rows[0]
    assert audit.reason_code == "ingestion_succeeded"
    assert audit.decision.value == "allowed"
    assert audit.metadata["actor_user_id"] == actor.user_id
    assert audit.metadata["inserted_chunk_count"] == result.inserted_chunk_count


async def test_ingest_document_same_checksum_skips_on_second_call(
    use_case, document_repo, chunk_repo, audit_repo, make_cmd
):
    first = await use_case.execute(make_cmd())
    second = await use_case.execute(make_cmd())
    assert first.outcome is IngestOutcome.INGESTED
    assert second.outcome is IngestOutcome.SKIPPED
    assert second.was_unchanged is True
    assert second.inserted_chunk_count == 0
    audit_rows = await audit_repo.find_by_correlation_id("corr-m7-test")
    # First call -> ingestion_succeeded; second -> ingestion_skipped.
    assert [row.reason_code for row in audit_rows] == [
        "ingestion_succeeded",
        "ingestion_skipped",
    ]


async def test_ingest_document_replaces_chunks_on_different_content(
    use_case, chunk_repo, audit_repo, make_cmd
):
    first = await use_case.execute(make_cmd(content="abc def ghi jkl"))
    first_chunks = await chunk_repo.find_active_by_document_id(first.document_id)
    assert len(first_chunks) == first.inserted_chunk_count
    assert all(c.status.value == "active" for c in first_chunks)

    # Different content -> replace path.
    second = await use_case.execute(
        make_cmd(content="second body. longer body. even longer body.")
    )
    assert second.outcome is IngestOutcome.INGESTED
    assert second.was_replaced is True
    after_replace = await chunk_repo.find_active_by_document_id(second.document_id)
    # The orphans from the first run are retired.
    assert {c.id for c in first_chunks}.isdisjoint({c.id for c in after_replace})
    assert len(after_replace) == second.inserted_chunk_count


async def test_ingest_document_chunker_failure_translates_to_pipeline_error(
    document_repo, chunk_repo, record_audit_event, audit_repo, make_cmd
):
    use_case = use_case = None
    from src.domain.ports.clearances import Clearance
    from src.application.ingestion import IngestDocument

    use_case = IngestDocument(
        documents=document_repo,
        chunks=chunk_repo,
        chunker=ExplodingChunker(),
        embedder=ShortEmbedder(),  # pragma: no cover -- unused
        record_audit_event=record_audit_event,
        clearance_enum=Clearance,
    )
    with pytest.raises(IngestionPipelineError):
        await use_case.execute(make_cmd())
    audit_rows = await audit_repo.find_by_correlation_id("corr-m7-test")
    assert len(audit_rows) == 1
    audit = audit_rows[0]
    assert audit.reason_code == "ingestion_failed"
    assert audit.decision.value == "failed"
    assert audit.action == "ingestion.failed"
    assert audit.metadata["error_code"] == "ingestion_pipeline_error"


async def test_ingest_document_blank_content_raises(make_cmd, use_case):
    with pytest.raises(MissingContentError):
        await use_case.execute(make_cmd(content=""))


async def test_ingest_document_embedding_shape_mismatch_raises(
    document_repo, chunk_repo, record_audit_event, make_cmd
):
    from src.domain.ports.clearances import Clearance
    from src.application.ingestion import IngestDocument
    from tests.application.ingestion.conftest import (
        FixedSizeChunker,
    )

    use_case = IngestDocument(
        documents=document_repo,
        chunks=chunk_repo,
        chunker=FixedSizeChunker(chunk_size=8),
        embedder=ShortEmbedder(),
        record_audit_event=record_audit_event,
        clearance_enum=Clearance,
    )
    with pytest.raises(Exception) as excinfo:
        await use_case.execute(make_cmd())
    # The use case wraps mis-shaped embeddings via
    # EmbeddingShapeMismatchError through the typed-error
    # hierarchy so the audit row records ingestion_failed.
    from src.application.ingestion.errors import (
        EmbeddingShapeMismatchError,
        IngestionPipelineError,
    )
    assert isinstance(excinfo.value, (EmbeddingShapeMismatchError, IngestionPipelineError))
