"""
Application-emitted reason codes for audit_logs.reason_code.

The seven M0 imm codes are emitted by the access-decision pure
function. Additional reason codes land in their own milestones;
this module is the single source of truth for the current
allowed set.

The repository layer rejects any reason_code outside this set
(fail-closed at the audit repository boundary).
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


# The current V1-allowed set. As new codes are added in their own
# milestones, extend this literal and re-run the audit suite.
ReasonCode = Literal[
    "missing_user_department",
    "missing_user_clearance",
    "missing_document_department",
    "missing_document_clearance",
    "department_mismatch",
    "clearance_insufficient",
    "allowed",
]


def is_allowed_reason_code(value: str) -> bool:
    """Return True iff `value` is one of the currently allowed codes."""
    return value in {
        "missing_user_department",
        "missing_user_clearance",
        "missing_document_department",
        "missing_document_clearance",
        "department_mismatch",
        "clearance_insufficient",
        "allowed",
    }
