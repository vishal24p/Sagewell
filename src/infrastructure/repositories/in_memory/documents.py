"""
In-memory DocumentRepository.

Persists only active Document rows by id and by
(source_system, source_id). All async methods run inside the
asyncio event loop.

M7 adds `upsert_by_source` for the ingestion use case. The
implementation is single-event-loop; the document id is allocated
atomically. Re-applying the same content_checksum yields
`was_unchanged=True`; re-applying a different content_checksum
yields `was_replaced=True` and the row's row-level mutable fields
are updated (id and created_at preserved).
"""
from datetime import datetime, timezone
from itertools import count
from typing import Iterable, Optional

from src.domain.ports.documents import (
    Document,
    DocumentRepository,
    DocumentStatus,
    DocumentUpsertCommand,
    DocumentUpsertResult,
)
from src.domain.ports.errors import PersistenceError


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._documents: dict[int, Document] = {}
        self._by_source: dict[tuple[str, str], int] = {}
        self._next_id = count(start=1)
        self._clock = lambda: datetime.now(timezone.utc)

    def set_clock(self, clock) -> None:
        """Test seam: provide a deterministic clock."""
        self._clock = clock

    def add(self, document: Document) -> Document:
        if document.id in self._documents:
            raise PersistenceError(f"document id conflict: {document.id}")
        self._documents[document.id] = document
        self._by_source[(document.source_system, document.source_id)] = document.id
        return document

    async def find_by_id(self, document_id: int) -> Optional[Document]:
        return self._documents.get(document_id)

    async def find_by_source(
        self,
        source_system: str,
        source_id: str,
    ) -> Optional[Document]:
        document_id = self._by_source.get((source_system, source_id))
        if document_id is None:
            return None
        return self._documents.get(document_id)

    async def find_active_by_ids(self, document_ids: Iterable[int]) -> list[Document]:
        ids = set(document_ids)
        return [
            document
            for document in self._documents.values()
            if document.id in ids and document.status == DocumentStatus.ACTIVE
        ]

    async def upsert_by_source(
        self,
        command: DocumentUpsertCommand,
    ) -> DocumentUpsertResult:
        existing = await self.find_by_source(
            command.source_system, command.source_id
        )
        if existing is None:
            new_id = next(self._next_id)
            now = self._clock()
            doc = Document(
                id=new_id,
                source_system=command.source_system,
                source_id=command.source_id,
                title=command.title,
                uri=command.uri,
                status=DocumentStatus.ACTIVE,
                department=command.department,
                required_clearance=command.required_clearance,
                content_checksum=command.content_checksum,
                created_at=now,
                updated_at=now,
            )
            self._documents[doc.id] = doc
            self._by_source[(doc.source_system, doc.source_id)] = doc.id
            return DocumentUpsertResult(
                document=doc,
                was_inserted=True,
                was_replaced=False,
                was_unchanged=False,
            )
        if existing.content_checksum == command.content_checksum:
            return DocumentUpsertResult(
                document=existing,
                was_inserted=False,
                was_replaced=False,
                was_unchanged=True,
            )
        updated = Document(
            id=existing.id,
            source_system=existing.source_system,
            source_id=existing.source_id,
            title=command.title,
            uri=command.uri,
            status=existing.status,
            department=command.department,
            required_clearance=command.required_clearance,
            content_checksum=command.content_checksum,
            created_at=existing.created_at,
            updated_at=self._clock(),
        )
        self._documents[existing.id] = updated
        self._by_source[(updated.source_system, updated.source_id)] = updated.id
        return DocumentUpsertResult(
            document=updated,
            was_inserted=False,
            was_replaced=True,
            was_unchanged=False,
        )
