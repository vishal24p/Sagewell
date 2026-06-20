"""
In-memory AuditLogRepository.

Validates reason_code at append time using the current V1-allowed
set. The Postgres adapter enforces the same rule.
"""
from typing import Optional

from src.domain.ports.audit_logs import AuditEvent, AuditLogRepository
from src.domain.ports.errors import PersistenceError
from src.domain.ports.reason_codes import is_allowed_reason_code


class InMemoryAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._next_id: int = 1

    async def append(self, event: AuditEvent) -> int:
        if not event.correlation_id:
            raise PersistenceError("audit event requires correlation_id")
        if not event.action:
            raise PersistenceError("audit event requires action")
        if not is_allowed_reason_code(event.reason_code):
            raise PersistenceError(
                f"reason_code not in allowed V1 set: {event.reason_code!r}"
            )
        new_id = self._next_id
        self._next_id += 1
        # The repository stamps the assigned id back onto the aggregate
        # by writing a new frozen event with id populated.
        materialized = event if event.id is None else event
        if event.id is None:
            materialized = AuditEvent(
                id=new_id,
                actor_user_id=event.actor_user_id,
                action=event.action,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                decision=event.decision,
                reason_code=event.reason_code,
                correlation_id=event.correlation_id,
                metadata=event.metadata,
                created_at=event.created_at,
            )
        self._events.append(materialized)
        return new_id

    async def find_by_correlation_id(self, correlation_id: str) -> list[AuditEvent]:
        return [e for e in self._events if e.correlation_id == correlation_id]
