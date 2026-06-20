"""Application-layer errors raised by the audit intake use case.

Two error categories split per M4 plan:

- `AuditEventError`: base class. Raised on input validation
  failures (missing correlation_id, missing action, decision
  outside the `AuditDecision` enum).

- `PersistenceFailure`: subclass. Raised when the underlying
  `AuditLogRepository.append()` raises `PersistenceError`
  (e.g., unknown reason_code, missing correlation_id/action
  at the repository boundary, JSON marshalling failure,
  Postgres connection lost). Per WORKFLOWS.md the failure
  surfaces as the canonical "audit write failed" signal;
  the future caller (M5+ middleware) chooses how to
  translate to an HTTP error.
"""
from __future__ import annotations


class AuditEventError(Exception):
    """Application-layer error raised by RecordAuditEvent."""


class PersistenceFailure(AuditEventError):
    """Raised when the AuditLogRepository could not persist the row."""


__all__ = ["AuditEventError", "PersistenceFailure"]
