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
the M10/M11/M12 reason codes via the
`is_allowed_reason_code()` predicate. The strict
`ReasonCode` Literal stays narrowed to the seven M0
codes; the application's predicate accumulates the
V1 allowed-codes set across milestones.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from src.domain.access.access_decision import Reason as AccessReason
from src.domain.ports.audit_logs import (
    AuditDecision,
    AuditEvent,
    AuditLogRepository,
)
from src.domain.ports.retrieval import RetrievalStageStats
from src.domain.ports.retrieval_logs import (
    RetrievalLog,
    RetrievalLogRepository,
)
from src.domain.ports.users import UserProjection as User


__all__ = [
    "RecordRetrievalLog",
    "RecordRetrievalLogCommand",
    "RecordGuardVerdict",
    "RecordGuardVerdictCommand",
]


_M0_REASON_STRINGS = frozenset({
    "allowed",
    "department_mismatch",
    "clearance_insufficient",
    "missing_user_department",
    "missing_user_clearance",
    "missing_document_department",
    "missing_document_clearance",
})

_OTHER_REASON_STRINGS = frozenset({
    "jwt_invalid",
    "ingestion_succeeded",
    "ingestion_skipped",
    "ingestion_failed",
})

_REASON_CODES_FROM_M0 = _M0_REASON_STRINGS | _OTHER_REASON_STRINGS
_GUARD_REASON_CODES = frozenset({
    "regex_passed",
    "regex_refused_high",
    "regex_refused_critical",
    "llm_guard_allow",
    "llm_guard_downgrade",
    "llm_guard_refuse",
})

# All V1 reason codes audit_logs may carry.
ALL_V1_REASON_CODES = frozenset(_REASON_CODES_FROM_M0) | _GUARD_REASON_CODES


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

    def __init__(self, *, repo: RetrievalLogRepository) -> None:
        self._repo = repo

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
            created_at=command.occurred_at or datetime.utcnow(),
        )
        return await self._repo.append(log)


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

    def __init__(self, *, repo: AuditLogRepository) -> None:
        self._repo = repo

    async def execute(self, command: RecordGuardVerdictCommand) -> int:
        if command.reason_code not in ALL_V1_REASON_CODES:
            raise ValueError(
                f"reason_code {command.reason_code!r} is not a V1 allowed code."
            )
        audit = AuditEvent(
            id=None,
            created_at=command.occurred_at or datetime.utcnow(),
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
