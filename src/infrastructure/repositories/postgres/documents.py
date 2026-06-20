"""
Postgres-backed DocumentRepository.

Active-row lookups only. Methods combine department + clearance at
the SQL level are deliberately absent; authorization is the
access-decision function's responsibility.
"""
from __future__ import annotations

from typing import Iterable, Optional

import asyncpg

from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import Document, DocumentRepository, DocumentStatus
from src.domain.ports.errors import PersistenceError


_CLEARANCE_BY_TEXT = {
    "PUBLIC": Clearance.PUBLIC,
    "INTERNAL": Clearance.INTERNAL,
    "CONFIDENTIAL": Clearance.CONFIDENTIAL,
    "RESTRICTED": Clearance.RESTRICTED,
}


def _coerce_document(row: asyncpg.Record) -> Document:
    try:
        status = DocumentStatus(row["status"])
    except ValueError as exc:
        raise PersistenceError(
            f"documents.status is not a V1 status: {row['status']!r}"
        ) from exc
    clearance = _CLEARANCE_BY_TEXT.get(row["required_clearance"])
    if clearance is None:
        raise PersistenceError(
            f"documents.required_clearance is not V1: {row['required_clearance']!r}"
        )
    return Document(
        id=row["id"],
        source_system=row["source_system"],
        source_id=row["source_id"],
        title=row["title"],
        uri=row["uri"],
        status=status,
        department=row["department"],
        required_clearance=clearance,
        content_checksum=row["content_checksum"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresDocumentRepository(DocumentRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_id(self, document_id: int) -> Optional[Document]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM documents WHERE id = $1",
                document_id,
            )
        return _coerce_document(row) if row is not None else None

    async def find_by_source(
        self,
        source_system: str,
        source_id: str,
    ) -> Optional[Document]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM documents "
                "WHERE source_system = $1 AND source_id = $2",
                source_system,
                source_id,
            )
        return _coerce_document(row) if row is not None else None

    async def find_active_by_ids(self, document_ids: Iterable[int]) -> list[Document]:
        ids = list(document_ids)
        if not ids:
            return []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM documents WHERE id = ANY($1::bigint[]) "
                "AND status = 'active'",
                ids,
            )
        return [_coerce_document(row) for row in rows]
