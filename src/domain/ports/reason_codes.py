"""
Application-emitted reason codes for audit_logs.reason_code.

The seven M0 imm codes are emitted by the access-decision pure
function. The repository layer rejects any reason_code outside
the currently allowed set (fail-closed at the audit
repository boundary). Adding new reason codes happens in the
owning milestone; this module is the single source of truth
for the current set.

V1 allowed set (M0 + M5 carve-out):

  M0 (access-decision pure function):
    - missing_user_department
    - missing_user_clearance
    - missing_document_department
    - missing_document_clearance
    - department_mismatch
    - clearance_insufficient
    - allowed

  M5 (RecordedAuditEvent on JWT validation failures):
    - jwt_invalid

The `ReasonCode` literal at the bottom remains the *strict*
type used by the access-decision pure function only; widening
it for the M5 JWT row would falsely advertise M5 reason codes
as legal RBAC outputs. New V1 reason codes land here as their
own milestones and extend `is_allowed_reason_code` (the
repository whitelist).
"""
from typing import Literal


# Reason codes emitted by the access-decision pure function.
ACCESS_DECISION_MISSING_USER_DEPARTMENT = "missing_user_department"
ACCESS_DECISION_MISSING_USER_CLEARANCE = "missing_user_clearance"
ACCESS_DECISION_MISSING_DOCUMENT_DEPARTMENT = "missing_document_department"
ACCESS_DECISION_MISSING_DOCUMENT_CLEARANCE = "missing_document_clearance"
ACCESS_DECISION_DEPARTMENT_MISMATCH = "department_mismatch"
ACCESS_DECISION_CLEARANCE_INSUFFICIENT = "clearance_insufficient"
ACCESS_DECISION_ALLOWED = "allowed"


# Reason codes emitted by the application layer for reasons other
# than the access-decision pure function. J-W-T authentication
# failures are recorded with this code (M5).
JWT_INVALID = "jwt_invalid"


# Reason codes emitted by the M7 ingestion application layer.
INGESTION_SUCCEEDED = "ingestion_succeeded"
INGESTION_SKIPPED = "ingestion_skipped"
INGESTION_FAILED = "ingestion_failed"


# Reason codes emitted by the access-decision pure function. The
# M5 `jwt_invalid` extension is intentionally NOT in this literal;
# the literal bounds the access-decision's output shape, not the
# repository's broader V1-allowed set.
ReasonCode = Literal[
    "missing_user_department",
    "missing_user_clearance",
    "missing_document_department",
    "missing_document_clearance",
    "department_mismatch",
    "clearance_insufficient",
    "allowed",
]


# The repository's V1-allowed set. As new reason codes are
# introduced in their own milestones, extend this set. The
# `is_allowed_reason_code` predicate below is the single hard
# validation point used by every adapter (in-memory + Postgres).
_ALLOWED_REASON_CODES: frozenset[str] = frozenset({
    "missing_user_department",
    "missing_user_clearance",
    "missing_document_department",
    "missing_document_clearance",
    "department_mismatch",
    "clearance_insufficient",
    "allowed",
    "jwt_invalid",
    "ingestion_succeeded",
    "ingestion_skipped",
    "ingestion_failed",
})


def is_allowed_reason_code(value: str) -> bool:
    """Return True iff `value` is one of the currently allowed codes.

    The repository's V1-allowed set is the union of the seven M0
    imm codes plus any reason codes introduced by their owning
    milestones. M5 introduces `jwt_invalid` for the JWT validation
    path; M7 introduces three ingestion outcome codes. The
    function returns True for all of these at every adapter
    boundary.
    """
    return value in _ALLOWED_REASON_CODES

