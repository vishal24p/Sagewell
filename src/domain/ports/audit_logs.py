"""
V1 AuditEvent aggregate and AuditLogRepository port.

`decision` is one of `allowed`, `denied`, `refused`, `failed`
per DATABASE_SCHEMA.md. `reason_code` is constrained to the
current V1-allowed set (see reason_codes.py); the repository
rejects other strings with PersistenceError (fail-closed).

`metadata` is `dict`; the application is responsible for redacting
secrets before calling `append`. The repository never redacts.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Protocol


class AuditDecision(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    REFUSED = "refused"
    FAILED = "failed"


@dataclass(frozen=True)
class AuditEvent:
    # `id` is None until the repository has appended the row. The
    # repository returns the populated id (or raises) so the caller
    # can chain observability IDs.
    id: Optional[int]
    actor_user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    decision: AuditDecision
    reason_code: str
    correlation_id: str
    metadata: dict
    created_at: datetime


class AuditLogRepository(Protocol):
    async def append(self, event: AuditEvent) -> int: ...

    async def find_by_correlation_id(self, correlation_id: str) -> list[AuditEvent]: ...
