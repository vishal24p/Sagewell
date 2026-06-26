"""
V1 Document aggregate and DocumentRepository port.

The Document aggregate carries every column the M1 schema names.
The access-decision pure function takes the M0 projection
(`Document.department`, `Document.required_clearance`); use
`Document.as_authorization_projection()` at the boundary.

The repository exposes only active-row lookups by id and source.
Methods that combine department + clearance at the SQL level are
deliberately absent: authorization is the access-decision function's
responsibility, never the repository's.

M7 adds `upsert_by_source` for the ingestion use case. The method
is idempotent on `(source_system, source_id)`: re-issuing the same
content_checksum yields no row insertion; re-issuing a different
content_checksum updates the row in place. `insert_or_return_unchanged`
returns the canonical Document (existing or freshly inserted).
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable, Optional, Protocol

from .clearances import Clearance


class DocumentStatus(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class Document:
    id: int
    source_system: str
    source_id: str
    title: str
    uri: Optional[str]
    status: DocumentStatus
    department: str
    required_clearance: Clearance
    content_checksum: str
    created_at: datetime
    updated_at: datetime

    def as_authorization_projection(self) -> "DocumentProjection":
        return DocumentProjection(
            department=self.department,
            required_clearance=self.required_clearance,
        )


@dataclass(frozen=True)
class DocumentProjection:
    """The minimal projection the access-decision pure function uses."""
    department: Optional[str]
    required_clearance: Optional[Clearance]


@dataclass(frozen=True)
class DocumentUpsertCommand:
    """The M7 ingestion input for the documents upsert path.

    The repository treats `content_checksum` as the canonical
    idempotence key on the document row: same checksum -> no
    update; different checksum -> update content_checksum /
    title / uri in place.
    """
    source_system: str
    source_id: str
    title: str
    uri: Optional[str]
    department: str
    required_clearance: Clearance
    content_checksum: str


@dataclass(frozen=True)
class DocumentUpsertResult:
    """Outcome of an `upsert_by_source` call.

    - `document`: the canonical Document row.
    - `was_inserted`: True when the row did not previously exist.
    - `was_replaced`: True when an existing row's content_checksum
      was different and the row was updated in place.
    - `was_unchanged`: True when the row already existed with the
      same content_checksum (the canonical M7 idempotence hit).
    """
    document: Document
    was_inserted: bool
    was_replaced: bool
    was_unchanged: bool


class DocumentRepository(Protocol):
    async def find_by_id(self, document_id: int) -> Optional[Document]: ...

    async def find_by_source(
        self,
        source_system: str,
        source_id: str,
    ) -> Optional[Document]: ...

    async def find_active_by_ids(
        self,
        document_ids: Iterable[int],
    ) -> list[Document]: ...

    async def upsert_by_source(
        self,
        command: DocumentUpsertCommand,
    ) -> DocumentUpsertResult: ...
