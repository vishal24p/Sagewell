"""M6 typed `WorkflowState`.

Every workflow run begins with a `WorkflowState`. The state is
the V1 contract between:

  - The API layer (M5 middleware hands the typed actor off as
    `state.actor` via ASGI `scope["state"]["actor"]`).
  - The application layer (this package).
  - The infrastructure layer (`src/infrastructure/langgraph/`).

The state is a frozen dataclass and is constructed only through
`WorkflowState.from_actor(...)` so anonymous execution cannot
slip in. The five required fields map directly to the
`{user_id, department, clearance, role, correlation_id}` shape
documented in ARCHITECTURE.md and V1/WORKFLOWS.md.

The role field is preserved verbatim from the JWT (per `POLICIES.md`):
role is reserved for UI behavior and auditing; it does NOT
participate in authorization. This module does not import the
domain access-decision.

The state carries a `query: Optional[str]` field for M6 (default
`None`). Future M7+ retrieval / M9+ workflow-wiring will read
the query and route through the LangGraph state machine. M6
intentionally keeps the query absent-by-default so a workflow
run that has no query remains well-typed.

The `query` is the only optional field. It exists so the M6
workflow skeleton can be invoked from a future API endpoint
without M7+M8 surface details (the field carries the user's
normalized question, not the raw HTTP body).
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Optional

from src.application.auth.dto import AuthActor
from src.application.workflow.errors import (
    AnonymousExecutionError,
    IncompleteActorError,
)


_REQUIRED_FIELDS: tuple[str, ...] = (
    "user_id",
    "department",
    "clearance",
    "role",
    "correlation_id",
)


def _is_blank(value: object) -> bool:
    """Return True iff `value` is None, '', or whitespace-only."""
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return not value.strip()


@dataclass(frozen=True)
class WorkflowState:
    """The typed state that flows through every V1 workflow run.

    Construction is gated. Direct `WorkflowState(...)` calls
    are supported for the framework adapter's internal channel
    wiring, but every application-side entry point goes through
    `from_actor` so anonymous execution is impossible.

    Fields:
      user_id: JWT `sub` claim verbatim.
      department: JWT `department` claim.
      clearance: JWT `clearance` claim (a clearance token; the
        access-decision pure function in `src/domain/access/`
        lowers it into the canonical hierarchy on use).
      role: JWT `role` claim (UI/behaviour/audit only).
      correlation_id: per-request UUID4 / X-Correlation-ID header
        value passed through from the API layer.
      query: optional user query; absent for M6. M7+ will read
        this field. Keeping it `None` at M6 means the M6 skeleton
        test can construct a typed state without proxying a real
        query.
    """

    user_id: str
    department: str
    clearance: str
    role: str
    correlation_id: str
    query: Optional[str] = field(default=None)

    def __post_init__(self) -> None:
        # Frozen dataclass: catch missing fields BEFORE the
        # framework sees the state. The constructor-level check
        # is a defense-in-depth companion to `from_actor`'s
        # typed-factory check.
        missing: list[str] = [
            name
            for name in _REQUIRED_FIELDS
            if _is_blank(getattr(self, name))
        ]
        if missing:
            raise IncompleteActorError(
                "WorkflowState requires non-empty "
                f"`{'`, `'.join(missing)}`; anonymous execution "
                "is forbidden at the M6 boundary."
            )

    @classmethod
    def from_actor(
        cls,
        actor: AuthActor,
        *,
        query: Optional[str] = None,
    ) -> "WorkflowState":
        """Construct a typed WorkflowState from an M5 `AuthActor`.

        Raises `IncompleteActorError` if any required field on
        the actor is blank. The typed factory is the canonical
        path for every caller (API layer, workflow entrypoint,
        tests). Direct constructor calls are reserved for the
        framework-adapter internals.
        """
        missing: list[str] = []
        for name in _REQUIRED_FIELDS:
            if _is_blank(getattr(actor, name)):
                missing.append(name)
        # Cross-check correlation_id depth: AuthActor must have
        # a correlation_id even if it equals the request's id;
        # the JWT-verified path always populates it.
        if missing:
            raise IncompleteActorError(
                "AuthActor missing required fields "
                f"`{'`, `'.join(missing)}` for WorkflowState "
                "construction; the V1 workflow forbids anonymous "
                "execution."
            )
        return cls(
            user_id=actor.user_id,
            department=actor.department,
            clearance=actor.clearance,
            role=actor.role,
            correlation_id=actor.correlation_id,
            query=query,
        )

    def with_query(self, query: str) -> "WorkflowState":
        """Return a new state with the `query` field populated."""
        if _is_blank(query):
            raise AnonymousExecutionError(
                "WorkflowState.with_query rejects blank queries; "
                "an empty question is not the canonical entry "
                "shape for the M6+ workflow."
            )
        return WorkflowState(
            user_id=self.user_id,
            department=self.department,
            clearance=self.clearance,
            role=self.role,
            correlation_id=self.correlation_id,
            query=query,
        )

    def required_field_names(self) -> tuple[str, ...]:
        """Return the names of every required (non-optional) field.

        Useful for diagnostics: the rollout / monitoring surfaces
        can ask the state which fields are non-empty-able.
        """
        return _REQUIRED_FIELDS

    def channel_keys(self) -> tuple[str, ...]:
        """Return the keys a LangGraph state channel needs to project.

        The framework adapter subscribes to these keys when
        binding `WorkflowState` to a `langgraph.graph.StateGraph`.
        Optional fields (currently only `query`) are listed
        alongside the required ones so the adapter can mark
        them optional in its channel schema.
        """
        return tuple(f.name for f in fields(self))


__all__ = ["WorkflowState"]


# Errors are re-exported at the package level so the application
# boundary (`from src.application.workflow import ...`) carries
# the typed-error hierarchy in one path.
from src.application.workflow.errors import (  # noqa: E402 - re-export
    AnonymousExecutionError,
    IncompleteActorError,
)


__all__ += ["AnonymousExecutionError", "IncompleteActorError"]
