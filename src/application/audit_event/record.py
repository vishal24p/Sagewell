"""`RecordAuditEvent` use case.

Single application-layer entry point for writing a V1 audit
event into the audit_logs table via the M2
`AuditLogRepository.append()` port.

Boundary contracts:

- Validates the input projection (no empty correlation_id,
  no empty action, decision must be an `AuditDecision`
  enum value).
- Stamps `created_at` from a `Clock` (defaults to UTC now).
- Calls the repository's `append()`.
- Translates a repository-side `PersistenceError` into the
  application-side `PersistenceFailure`. Per WORKFLOWS.md
  ("audit write fails -> do not return a response"); the
  use case surfaces the failure as a typed error; the future
  caller (M5+) owns the "do not return a response" rule.

What this use case does NOT do at M4:

- It does not wire a database pool. Tests pass an explicit
  `AuditLogRepository`; M5+ callers will construct a real
  Postgres-backed repo at runtime.
- It does not appear in the FastAPI request pipeline. M4
  ships no audit-write middleware and no `/v1/...` route
  consumes it.

Import direction:

- Imports from `src/domain/ports/` only.
- Imports from `src/application/audit_event/clock/errors/dto`.
- Does NOT import from `src/api/`, `src/infrastructure/`,
  fastapi, asyncpg, or any framework SDK.
"""
from __future__ import annotations

from typing import Optional

from src.application.audit_event.clock import Clock, SystemClock
from src.application.audit_event.dto import (
    AuditEventId,
    RecordAuditCommand,
)
from src.application.audit_event.errors import (
    AuditEventError,
    PersistenceFailure,
)
from src.domain.ports.audit_logs import (
    AuditDecision,
    AuditEvent,
    AuditLogRepository,
)
from src.domain.ports.errors import PersistenceError


class RecordAuditEvent:
    """Single use case. Persists a single audit row via the repository."""

    def __init__(
        self,
        repo: AuditLogRepository,
        *,
        clock: Optional[Clock] = None,
    ) -> None:
        self._repo = repo
        self._clock = clock if clock is not None else SystemClock()

    async def __call__(self, cmd: RecordAuditCommand) -> AuditEventId:
        if not cmd.correlation_id:
            raise AuditEventError(
                "record_audit_event requires correlation_id"
            )
        if not cmd.action:
            raise AuditEventError(
                "record_audit_event requires action"
            )
        if not isinstance(cmd.decision, AuditDecision):
            raise AuditEventError(
                "decision must be an AuditDecision enum value"
            )

        event = AuditEvent(
            id=None,
            actor_user_id=cmd.actor_user_id,
            action=cmd.action,
            resource_type=cmd.resource_type,
            resource_id=cmd.resource_id,
            decision=cmd.decision,
            reason_code=cmd.reason_code,
            correlation_id=cmd.correlation_id,
            metadata=dict(cmd.metadata or {}),
            created_at=self._clock.now(),
        )

        try:
            new_id = await self._repo.append(event)
        except PersistenceError as exc:
            raise PersistenceFailure(str(exc)) from exc

        return AuditEventId(new_id)


__all__ = ["RecordAuditEvent"]
