"""M6 workflow typed-error hierarchy.

The application workflow package raises these typed errors when
construction or validation fails. They sub-class
`WorkflowDomainError` so downstream consumers (M9+) can catch the
broad category without coupling to specific subclasses, but each
subclass carries a stable `.code` slug for audit-log mapping
when future milestones wire workflow failures to M12 audit
plumbing.

`AnonymousExecutionError` is the canonical "the workflow must
not start without an authenticated actor" signal. M6 raises this
when:
  - any of `user_id` / `department` / `clearance` / `role` /
    `correlation_id` is empty or whitespace-only
    (`IncompleteActorError`), or
  - the typed factory is bypassed through any path that would
    produce a partially-populated WorkflowState
    (`AnonymousExecutionError` covers the broader failure).
"""
from __future__ import annotations


class WorkflowDomainError(Exception):
    """Base for every typed workflow failure."""

    code: str = "workflow_failed"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__


class AnonymousExecutionError(WorkflowDomainError):
    """The workflow state machine was asked to start without an authenticated actor.

    Per AGENTS.md and ARCHITECTURE.md (M6 description): the
    workflow refuses to start if `user_id`, `department`,
    `clearance`, `role`, or `correlation_id` is missing. The
    canonical typed signal prevents anonymous execution paths
    from sneaking into the workflow at the M6+ boundary.
    """

    code: str = "anonymous_execution"


class IncompleteActorError(AnonymousExecutionError):
    """At least one of the five required WorkflowState fields is empty.

    Sub-class of `AnonymousExecutionError` so single-exception
    catch surfaces a useful code; the message carries the empty
    field list for diagnostics. Carries a stable code slug for
    audit rows wired up in M12.
    """

    code: str = "incomplete_actor"


__all__ = [
    "AnonymousExecutionError",
    "IncompleteActorError",
    "WorkflowDomainError",
]
