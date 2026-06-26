"""
Postgres-backed DocumentRepository.

Active-row lookups only. Methods combine department + clearance at
the SQL level are deliberately absent; authorization is the
access-decision function's responsibility.

M7 adds `upsert_by_source` for the ingestion use case. The
implementation uses one INSERT ... ON CONFLICT ... DO UPDATE
statement so a write does not race against a concurrent
ingester on the same (source_system, source_id) key. The
`was_inserted` / `was_replaced` / `was_unchanged` distinction
derived from the RETURNING clause plus an `xmax = 0` heuristic
that asyncpg exposes when the row was just inserted by the
current transaction.
"""
from __future__ import annotations

from typing import Iterable, Optional

import asyncpg

from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import (
    Document,
    DocumentRepository,
    DocumentStatus,
    DocumentUpsertCommand,
    DocumentUpsertResult,
)
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

    async def upsert_by_source(
        self,
        command: DocumentUpsertCommand,
    ) -> DocumentUpsertResult:
        # Snapshot the existing row (if any) in the same
        # transaction so the (was_inserted, was_replaced,
        # was_unchanged) outcome is consistent with the
        # RETURNING-row that follows.
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                existing = await conn.fetchrow(
                    "SELECT id, content_checksum, created_at, "
                    "updated_at, status "
                    "FROM documents "
                    "WHERE source_system = $1 AND source_id = $2 "
                    "FOR UPDATE",
                    command.source_system,
                    command.source_id,
                )
                row = await conn.fetchrow(
                    "INSERT INTO documents ("
                    "  source_system, source_id, title, uri,"
                    "  status, department, required_clearance,"
                    "  content_checksum"
                    ") VALUES ($1, $2, $3, $4, 'active', $5, $6, $7) "
                    "ON CONFLICT (source_system, source_id) DO UPDATE "
                    "SET title = EXCLUDED.title,"
                    "    uri = EXCLUDED.uri,"
                    "    department = EXCLUDED.department,"
                    "    required_clearance = EXCLUDED.required_clearance,"
                    "    content_checksum = EXCLUDED.content_checksum,"
                    "    updated_at = NOW() "
                    "RETURNING *",
                    command.source_system,
                    command.source_id,
                    command.title,
                    command.uri,
                    command.department,
                    command.required_clearance.value,
                    command.content_checksum,
                )
        doc = _coerce_document(row)
        if existing is None:
            return DocumentUpsertResult(
                document=doc,
                was_inserted=True,
                was_replaced=False,
                was_unchanged=False,
            )
        if existing["content_checksum"] == command.content_checksum:
            return DocumentUpsertResult(
                document=doc,
                was_inserted=False,
                was_replaced=False,
                was_unchanged=True,
            )
        return DocumentUpsertResult(
            document=doc,
            was_inserted=False,
            was_replaced=True,
            was_unchanged=False,
        )
