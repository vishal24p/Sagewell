"""Data-transfer objects for the audit intake use case.

- `RecordAuditCommand`: the application's projection of an
  audit record. Mirrors `AuditEvent` minus the DB-assigned
  `id` and `created_at`; the use case stamps the timestamp.

- `AuditEventId`: the assigned id returned by the repository
  after a successful append. NewType over `int`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import NewType, Optional

from src.domain.ports.audit_logs import AuditDecision


AuditEventId = NewType("AuditEventId", int)


@dataclass(frozen=True)
class RecordAuditCommand:
    """Application-side input for `RecordAuditEvent`."""

    actor_user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    decision: AuditDecision
    reason_code: str
    correlation_id: str
    metadata: Optional[dict] = None


__all__ = ["AuditEventId", "RecordAuditCommand"]
