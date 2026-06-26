"""M7 `IngestDocument` use case.

The use case wires together:

  - The M5 typed `AuthActor` (caller identity for the audit row).
  - The `documents` / `chunks` repositories (writes).
  - The `DocumentChunkerProtocol` (chunking) and
    `EmbeddingModelProtocol` (vectorization).
  - The M4 `RecordAuditEvent` use case (job-outcome audit row).

Idempotence:

  - `content_checksum` is computed on the supplied raw content
    (window-CR normalization + sha256). If the document
    already exists with the same checksum, the use case
    emits an `ingestion_skipped` audit row and returns
    `IngestOutcome.SKIPPED`. NO chunks are touched.
  - A different checksum triggers `documents.upsert_by_source`
    + `chunks.replace_for_document` in that order. The use
    case emits an `ingestion_succeeded` audit row with the
    inserted chunk count in `metadata` and returns
    `IngestOutcome.INGESTED`. The replaced chunks are not
    searchable after the call (the Postgres adapter marks
    the previous active chunks `retired` before the
    multi-row INSERT, in a single transaction).

Failure path:

  - Any unexpected exception inside the chunker / embedder /
    repository pipeline is captured, the audit row emits
    `reason_code = "ingestion_failed"`, and the use case
    raises `IngestionPipelineError` for the caller to
    observe. The mid-call failure on the Postgres side
    rolls the transaction back; on the in-memory adapter
    the synchronous list update leaves no partial state.

The use case is async (uses async repositories). The chunker
and embedder are synchronous; the application payload is
small enough for in-process chunking at M7.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Optional, Sequence

from src.domain.ports.audit_logs import AuditDecision
from src.domain.ports.chunks import (
    EMBEDDING_DIM,
    ChunkDraft,
)
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import (
    DocumentUpsertCommand,
)
from src.domain.ports.errors import PersistenceError
from src.domain.ports.ingestion import (
    ChunkSegment,
    DocumentChunkerProtocol,
    EmbeddingModelProtocol,
)
from src.domain.ports.reason_codes import (
    INGESTION_FAILED,
    INGESTION_SKIPPED,
    INGESTION_SUCCEEDED,
)

from src.application.audit_event.dto import RecordAuditCommand
from src.application.audit_event.record import RecordAuditEvent
from src.application.auth.dto import AuthActor
from src.application.ingestion.checksum import normalize_content_checksum
from src.application.ingestion.errors import (
    EmbeddingShapeMismatchError,
    IngestionDomainError,
    IngestionPipelineError,
    MissingContentError,
)


class IngestOutcome(str, Enum):
    """Stable outcome slug for the M7 ingestion use case.

    - `INGESTED`: rows were inserted; replaced chunks are no
      longer searchable.
    - `SKIPPED`: the supplied content_checksum matched an
      existing document row; no chunk rows were touched.
    - `FAILED`: the pipeline raised; the audit row carries
      `ingestion_failed` and a `pipeline_error` slug in
      metadata.
    """

    INGESTED = "ingested"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class IngestDocumentCommand:
    """The M7 application use case input.

    `actor` is the M5 typed AuthActor who initiated the
    ingestion (the audit_logs row carries this actor).
    `source_system` + `source_id` form the unique key on
    `documents` and is the idempotence handle. `content` is
    the raw bytes-equivalent (string); `title` / `uri` are
    the document's display fields. `department` and
    `required_clearance` are the document's authorization
    fields; they are persisted verbatim on the row.
    """

    actor: AuthActor
    source_system: str
    source_id: str
    title: str
    uri: Optional[str]
    department: str
    required_clearance: Clearance
    content: str
    metadata: dict = field(default_factory=dict)
    correlation_id: Optional[str] = None

    def with_correlation_id(self, correlation_id: str) -> "IngestDocumentCommand":
        return IngestDocumentCommand(
            actor=self.actor,
            source_system=self.source_system,
            source_id=self.source_id,
            title=self.title,
            uri=self.uri,
            department=self.department,
            required_clearance=self.required_clearance,
            content=self.content,
            metadata=self.metadata,
            correlation_id=correlation_id,
        )


@dataclass(frozen=True)
class IngestDocumentResult:
    """The M7 application use case output."""

    outcome: IngestOutcome
    document_id: Optional[int]
    content_checksum: str
    inserted_chunk_count: int = 0
    retired_chunk_count: int = 0
    was_inserted: bool = False
    was_replaced: bool = False
    was_unchanged: bool = False


class IngestDocument:
    """The M7 ingestion use case.

    Constructor dependencies:

      - `documents`: `DocumentRepository` (M2 + M7 writes).
      - `chunks`: `ChunkRepository` (M2 + M7 writes).
      - `chunker`: `DocumentChunkerProtocol`
        (defaults to no-op chunker if unset).
      - `embedder`: `EmbeddingModelProtocol`
        (defaults to deterministic-hash stub if unset).
      - `record_audit_event`: M4 use case. Required.
      - `clearance_enum`: the V1 Clearance type. Required.
    """

    def __init__(
        self,
        *,
        documents,
        chunks,
        chunker: DocumentChunkerProtocol,
        embedder: EmbeddingModelProtocol,
        record_audit_event: RecordAuditEvent,
        clearance_enum,
    ) -> None:
        self._documents = documents
        self._chunks = chunks
        self._chunker = chunker
        self._embedder = embedder
        self._record_audit_event = record_audit_event
        self._clearance_enum = clearance_enum

    async def execute(
        self, command: IngestDocumentCommand
    ) -> IngestDocumentResult:
        if not command.content or not command.content.strip():
            raise MissingContentError(
                "IngestDocument.execute requires non-empty content."
            )
        correlation_id = command.correlation_id or command.actor.correlation_id
        try:
            content_checksum = normalize_content_checksum(command.content)
            upsert_cmd = DocumentUpsertCommand(
                source_system=command.source_system,
                source_id=command.source_id,
                title=command.title,
                uri=command.uri,
                department=command.department,
                required_clearance=command.required_clearance,
                content_checksum=content_checksum,
            )
            upsert_result = await self._documents.upsert_by_source(upsert_cmd)
            document = upsert_result.document

            if upsert_result.was_unchanged:
                # Idempotence hit. No chunk writes. Audit row.
                await self._emit_audit(
                    command=command,
                    correlation_id=correlation_id,
                    outcome=INGESTION_SKIPPED,
                    document_id=document.id,
                    inserted_chunk_count=0,
                    retired_chunk_count=0,
                    was_inserted=False,
                    was_replaced=False,
                    was_unchanged=True,
                )
                return IngestDocumentResult(
                    outcome=IngestOutcome.SKIPPED,
                    document_id=document.id,
                    content_checksum=content_checksum,
                    inserted_chunk_count=0,
                    retired_chunk_count=0,
                    was_unchanged=True,
                )

            # Walk: chunk -> embed -> replace.
            segments: Sequence[ChunkSegment] = self._chunker.chunk(command.content)
            drafts = self._build_drafts(
                document_id=document.id, segments=segments
            )
            replace_result = await self._chunks.replace_for_document(
                document_id=document.id,
                drafts=drafts,
            )

            await self._emit_audit(
                command=command,
                correlation_id=correlation_id,
                outcome=INGESTION_SUCCEEDED,
                document_id=document.id,
                inserted_chunk_count=len(replace_result.inserted_chunks),
                retired_chunk_count=len(replace_result.retired_chunk_ids),
                was_inserted=upsert_result.was_inserted,
                was_replaced=upsert_result.was_replaced,
                was_unchanged=False,
            )
            return IngestDocumentResult(
                outcome=IngestOutcome.INGESTED,
                document_id=document.id,
                content_checksum=content_checksum,
                inserted_chunk_count=len(replace_result.inserted_chunks),
                retired_chunk_count=len(replace_result.retired_chunk_ids),
                was_inserted=upsert_result.was_inserted,
                was_replaced=upsert_result.was_replaced,
            )
        except IngestionDomainError as exc:
            await self._emit_failure_audit(
                command=command,
                correlation_id=correlation_id,
                error_code=exc.code,
                message=str(exc),
            )
            raise
        except (PersistenceError,) as exc:
            await self._emit_failure_audit(
                command=command,
                correlation_id=correlation_id,
                error_code=IngestionPipelineError.code,
                message=str(exc),
            )
            raise IngestionPipelineError(str(exc)) from exc
        except Exception as exc:
            await self._emit_failure_audit(
                command=command,
                correlation_id=correlation_id,
                error_code=IngestionPipelineError.code,
                message=str(exc),
            )
            raise IngestionPipelineError(str(exc)) from exc

    # ------------------------------------------------------------------
    # The application-package boundary. Self-contained helpers below.
    # ------------------------------------------------------------------

    def _build_drafts(
        self,
        *,
        document_id: int,
        segments: Iterable[ChunkSegment],
    ) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for segment in segments:
            if segment.ordinal < 0:
                raise EmbeddingShapeMismatchError(
                    "Chunk ordinal must be non-negative; got "
                    f"{segment.ordinal} for document {document_id}."
                )
            text = segment.text
            if not text.strip():
                continue
            embedding = self._embedder.embed(text)
            if len(embedding) != EMBEDDING_DIM:
                raise EmbeddingShapeMismatchError(
                    f"EmbeddingModel.embed returned {len(embedding)} "
                    f"dimensions; expected {EMBEDDING_DIM}."
                )
            drafts.append(
                ChunkDraft(
                    document_id=document_id,
                    ordinal=segment.ordinal,
                    text=text,
                    text_search=text,
                    embedding=embedding,
                    metadata=segment.metadata,
                    token_count=len(text.split()),
                )
            )
        return drafts

    async def _emit_audit(
        self,
        *,
        command: IngestDocumentCommand,
        correlation_id: str,
        outcome: str,
        document_id: int,
        inserted_chunk_count: int,
        retired_chunk_count: int,
        was_inserted: bool,
        was_replaced: bool,
        was_unchanged: bool,
    ) -> None:
        await self._record_audit_event(
            RecordAuditCommand(
                actor_user_id=None,
                action="ingestion.completed",
                resource_type="document",
                resource_id=str(document_id),
                decision=(
                    AuditDecision.ALLOWED
                    if outcome == INGESTION_SUCCEEDED
                    else AuditDecision.DENIED
                ),
                reason_code=outcome,
                correlation_id=correlation_id,
                metadata={
                    "source_system": command.source_system,
                    "source_id": command.source_id,
                    "inserted_chunk_count": inserted_chunk_count,
                    "retired_chunk_count": retired_chunk_count,
                    "was_inserted": was_inserted,
                    "was_replaced": was_replaced,
                    "was_unchanged": was_unchanged,
                    "actor_user_id": command.actor.user_id,
                    "actor_department": command.actor.department,
                    "actor_clearance": command.actor.clearance,
                },
            )
        )

    async def _emit_failure_audit(
        self,
        *,
        command: IngestDocumentCommand,
        correlation_id: str,
        error_code: str,
        message: str,
    ) -> None:
        await self._record_audit_event(
            RecordAuditCommand(
                actor_user_id=None,
                action="ingestion.failed",
                resource_type="document",
                resource_id=f"{command.source_system}:{command.source_id}",
                decision=AuditDecision.FAILED,
                reason_code=INGESTION_FAILED,
                correlation_id=correlation_id,
                metadata={
                    "source_system": command.source_system,
                    "source_id": command.source_id,
                    "error_code": error_code,
                    "error_message": message,
                    "actor_user_id": command.actor.user_id,
                    "actor_department": command.actor.department,
                    "actor_clearance": command.actor.clearance,
                },
            )
        )


__all__ = [
    "IngestDocument",
    "IngestDocumentCommand",
    "IngestDocumentResult",
    "IngestOutcome",
    "IngestionPipelineError",
    "MissingContentError",
    "EmbeddingShapeMismatchError",
]
