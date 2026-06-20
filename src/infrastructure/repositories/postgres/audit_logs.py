"""
Postgres-backed AuditLogRepository.

Validates reason_code at append time using the current V1-allowed
set. Returns the assigned `id`.
"""
from __future__ import annotations

from typing import Optional

import asyncpg

from src.domain.ports.audit_logs import AuditDecision, AuditEvent, AuditLogRepository
from src.domain.ports.errors import PersistenceError
from src.domain.ports.reason_codes import is_allowed_reason_code


_DECISION_BY_TEXT = {
    "allowed": AuditDecision.ALLOWED,
    "denied": AuditDecision.DENIED,
    "refused": AuditDecision.REFUSED,
    "failed": AuditDecision.FAILED,
}


def _coerce_event(row: asyncpg.Record) -> AuditEvent:
    decision_text = row["decision"]
    decision = _DECISION_BY_TEXT.get(decision_text)
    if decision is None:
        raise PersistenceError(
            f"audit_logs.decision is not V1: {decision_text!r}"
        )
    return AuditEvent(
        id=row["id"],
        actor_user_id=row["actor_user_id"],
        action=row["action"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        decision=decision,
        reason_code=row["reason_code"],
        correlation_id=row["correlation_id"],
        metadata=row["metadata"] or {},
        created_at=row["created_at"],
    )


class PostgresAuditLogRepository(AuditLogRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def append(self, event: AuditEvent) -> int:
        if not event.correlation_id:
            raise PersistenceError("audit event requires correlation_id")
        if not event.action:
            raise PersistenceError("audit event requires action")
        if not is_allowed_reason_code(event.reason_code):
            raise PersistenceError(
                f"reason_code not in allowed V1 set: {event.reason_code!r}"
            )
        async with self._pool.acquire() as conn:
            new_id = await conn.fetchval(
                "INSERT INTO audit_logs ("
                "  actor_user_id, action, resource_type, resource_id,"
                "  decision, reason_code, correlation_id, metadata, created_at"
                ") VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9) "
                "RETURNING id",
                event.actor_user_id,
                event.action,
                event.resource_type,
                event.resource_id,
                event.decision.value,
                event.reason_code,
                event.correlation_id,
                event.metadata,
                event.created_at,
            )
        if new_id is None:
            raise PersistenceError("audit_logs INSERT returned no id")
        return int(new_id)

    async def find_by_correlation_id(self, correlation_id: str) -> list[AuditEvent]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM audit_logs WHERE correlation_id = $1 "
                "ORDER BY id ASC",
                correlation_id,
            )
        return [_coerce_event(row) for row in rows]
