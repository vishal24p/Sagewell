"""Typed-error hierarchy for the M8 retrieval application layer.

Boundary contract:

  - `AccessDecisionUnavailableError` is raised when the M0
    access-decision pure function yields no projection we can
    translate into an `AccessPolicyFilter`. The M0 function
    always returns a tuple; the projection step is pure; this
    error covers the failure path where the tuple is not
    well-shaped (defense in depth).
  - `EmptyRetrievalError` is raised when every retrieval
    stage returns zero candidates. Per `WORKFLOWS.md`, the
    primary request path handles retrieval-empty with 503.
"""
from __future__ import annotations


class RetrievalDomainError(Exception):
    """Base for every retrieval application error."""

    code: str = "retrieval_failed"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.__class__.__name__)


class AccessDecisionUnavailableError(RetrievalDomainError):
    """Raised when the access-decision projection is malformed.

    The M0 pure function returns `(allowed, reason)`; the
    projection step MUST be able to translate a successful
    `allowed=True` decision into an `AccessPolicyFilter`.
    """

    code: str = "access_decision_unavailable"


class EmptyRetrievalError(RetrievalDomainError):
    """Raised when every retrieval stage returns zero candidates.

    Per `WORKFLOWS.md`, empty-retrieval at the M6 workflow
    boundary is a 503; the M8 orchestrator raises this so
    the future M6 / M9 surface can handle it explicitly.
    """

    code: str = "retrieval_empty"


__all__ = [
    "RetrievalDomainError",
    "AccessDecisionUnavailableError",
    "EmptyRetrievalError",
]
