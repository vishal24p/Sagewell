"""M12 -- Audit and Retrieval Logs complete.

This package owns the application-side write use cases
that bind the M8 retrieval stage-stats and the M10/M11
guard rails to the `audit_logs` and `retrieval_logs`
repositories.

Use cases:

  - `RecordRetrievalLog`: writes the typed
    `RetrievalStageStats` from M8 + the actor projection
    + the policy_filter projection to a `retrieval_logs`
    row.
  - `RecordGuardVerdict`: writes a typed
    `audit_logs` row for a Regex Guard or LLM Guard
    verdict with one of the M10/M11 M12 reason codes.

These use cases extend the M4 audit_intake surface with
the M10/M11/M12 reason codes via the canonical
`assert_is_allowed_reason_code()` predicate defined in
`src/domain/ports/reason_codes.py`. The canonical set is
the single source of truth across both the
application-layer validator (this module) and the
repository-layer validator (in-memory + Postgres
adapters). The strict `ReasonCode` Literal stays narrowed
to the seven M0 codes; the broader canonical set is the
union of M0 + M5 + M7 + M10/M11 codes.

Both use cases accept an optional `Clock` injection
(`src.application.audit_event.clock.Clock`). When
supplied, `created_at` is taken from `clock.now()` so
the audit-rows are timezone-aware and the deprecated
`datetime.utcnow()` path is dormant on production
callers.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Iterable, Optional

if TYPE_CHECKING:
    from src.application.audit_event.clock import Clock

from src.domain.access.access_decision import Reason as AccessReason
from src.domain.ports.audit_logs import (
    AuditDecision,
    AuditEvent,
    AuditLogRepository,
)
from src.domain.ports.reason_codes import (
    ALLOWED_REASON_CODES,
    assert_is_allowed_reason_code,
)
from src.domain.ports.retrieval import RetrievalStageStats
from src.domain.ports.retrieval_logs import (
    RetrievalLog,
    RetrievalLogRepository,
)
from src.domain.ports.users import UserProjection as User


__all__ = [
    "ALL_V1_REASON_CODES",
    "RecordRetrievalLog",
    "RecordRetrievalLogCommand",
    "RecordGuardVerdict",
    "RecordGuardVerdictCommand",
]


# The allowed-code set is owned by the domain port. This module re-exports
# it under the historical name `ALL_V1_REASON_CODES` so existing imports
# (`from src.application.observability.logs import ALL_V1_REASON_CODES`)
# keep working. The binding is identity (not a copy), so any future
# extension to the canonical set in the domain port automatically
# propagates here without an additional edit in this module.
ALL_V1_REASON_CODES = ALLOWED_REASON_CODES


@dataclass(frozen=True)
class RecordRetrievalLogCommand:
    """The M8 -> retrieval_logs write command.

    - `stage_stats`: the typed `RetrievalStageStats` from
      the M8 orchestrator.
    - `query_text`: the user query (post-regex-guard).
    - `policy_filter`: the M8 typed projection dict.
    - `retrieval_config`: capability-shape dict (model
      names / hyperparameters). Capability-deferred
      to the owning adoption milestones.
    - `actor_user_id`: the actor subject (`user_id` from
      the M5 typed `AuthActor`, the JWT `sub` claim).
      Resolves to `int` if numeric; falls back to `0`
      for non-numeric subjects.
    - `correlation_id`: per-request trace.
    - `occurred_at`: optional clock-driven timestamp.
      Defaults to `None`; the repository layer
      sets `created_at` itself.
    """

    stage_stats: RetrievalStageStats
    query_text: str
    policy_filter: dict
    retrieval_config: dict
    actor_user_id: str | int | None
    correlation_id: str
    occurred_at: Optional[datetime] = None


class RecordRetrievalLog:
    """Use case -- writes a single retrieval_logs row.

    The use case is the canonical call site after the
    M9 pipeline completes. It refuses to write rows
    whose payload cannot be serialized as a dict; the
    `RetrievalLog` aggregate carries plain mapping
    shapes only.
    """

    def __init__(
        self,
        *,
        repo: RetrievalLogRepository,
        clock: Optional["Clock"] = None,
    ) -> None:
        self._repo = repo
        self._clock: Optional["Clock"] = clock

    async def execute(self, command: RecordRetrievalLogCommand) -> int:
        stats_dict = dataclasses.asdict(command.stage_stats)
        # Reconcile the policy_filter dict shape so the JSON
        # column carries the typed projection verbatim.
        policy = dict(command.policy_filter or {})
        config = dict(command.retrieval_config or {})
        log = RetrievalLog(
            id=None,
            actor_user_id=_resolve_actor_id(command.actor_user_id),
            query_text=command.query_text,
            policy_filter=policy,
            retrieval_config=config,
            candidate_counts=stats_dict,
            correlation_id=command.correlation_id,
            created_at=_resolve_created_at(command.occurred_at, self._clock),
        )
        return await self._repo.append(log)


def _resolve_created_at(
    occurred_at: Optional[datetime], clock: Optional["Clock"]
) -> datetime:
    """Return a timezone-aware timestamp.

    Order:
      1. explicit `occurred_at` wins;
      2. injected `Clock.now()` returns timezone-aware datetime;
      3. unconfigured call falls back to `datetime.utcnow()`
         (the legacy behaviour carried from Issue 05 -- the
          production callers always inject Clock so this
          branch is dormant).
    """
    if occurred_at is not None:
        return occurred_at
    if clock is not None:
        return clock.now()
    return datetime.now(tz=timezone.utc)


def _resolve_actor_id(actor_id: str | int | None) -> int:
    """Best-effort numeric actor id for retrieval_logs.actor_user_id.

    The M5 actor projection carries the JWT `sub` claim
    as `user_id: str`. The retrieval_logs schema expects
    an integer. Tests / development subjects are
    alphanumeric; the helper returns `0` for any
    non-numeric subject so the row is durable even when
    the actor is not yet `users` `id`. Production
    deployments pin the JWT subject to the canonical
    `users` row.
    """
    if actor_id is None:
        return 0
    try:
        return int(actor_id)
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class RecordGuardVerdictCommand:
    """The M10/M11/M12 -> audit_logs write command."""

    actor_user_id: Optional[int]
    correlation_id: str
    action: str
    reason_code: str
    metadata: dict
    occurred_at: Optional[datetime] = None


class RecordGuardVerdict:
    """Use case -- writes a single audit_logs row for a guard verdict.

    The use case is the canonical call site after the
    M10 Regex Guard or M11 LLM Guard produces a verdict.
    It validates the reason_code against the V1
    allowed-codes predicate so the row carries only
    legal codes.
    """

    def __init__(
        self,
        *,
        repo: AuditLogRepository,
        clock: Optional["Clock"] = None,
    ) -> None:
        self._repo = repo
        self._clock: Optional["Clock"] = clock

    async def execute(self, command: RecordGuardVerdictCommand) -> int:
        assert_is_allowed_reason_code(command.reason_code)
        audit = AuditEvent(
            id=None,
            created_at=_resolve_created_at(command.occurred_at, self._clock),
            actor_user_id=command.actor_user_id,
            action=command.action,
            resource_type=None,
            resource_id=None,
            reason_code=command.reason_code,
            decision=AuditDecision.ALLOWED,
            metadata=dict(command.metadata or {}),
            correlation_id=command.correlation_id,
        )
        return await self._repo.append(audit)
