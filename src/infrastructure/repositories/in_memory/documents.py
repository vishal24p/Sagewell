"""
In-memory DocumentRepository.

Persists only active Document rows by id and by
(source_system, source_id). All async methods run inside the
asyncio event loop.
"""
from typing import Iterable, Optional

from src.domain.ports.documents import Document, DocumentRepository, DocumentStatus
from src.domain.ports.errors import PersistenceError


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._documents: dict[int, Document] = {}

    def add(self, document: Document) -> Document:
        if document.id in self._documents:
            raise PersistenceError(f"document id conflict: {document.id}")
        self._documents[document.id] = document
        return document

    async def find_by_id(self, document_id: int) -> Optional[Document]:
        return self._documents.get(document_id)

    async def find_by_source(
        self,
        source_system: str,
        source_id: str,
    ) -> Optional[Document]:
        for document in self._documents.values():
            if document.source_system == source_system and document.source_id == source_id:
                return document
        return None

    async def find_active_by_ids(self, document_ids: Iterable[int]) -> list[Document]:
        ids = set(document_ids)
        return [
            document
            for document in self._documents.values()
            if document.id in ids and document.status == DocumentStatus.ACTIVE
        ]
