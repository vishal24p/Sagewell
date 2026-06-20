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
