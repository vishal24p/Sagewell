from typing import Tuple

from .clearances import Clearance
from .models import Document, User

# Result is always a tuple. Never raise as an authorization outcome.
# Fail-closed: any missing input yields (False, reason).
AccessResult = Tuple[bool, str]


# Reason codes (stable for tests and downstream call sites).
class Reason:
    MISSING_USER_DEPARTMENT = "missing_user_department"
    MISSING_USER_CLEARANCE = "missing_user_clearance"
    MISSING_DOCUMENT_DEPARTMENT = "missing_document_department"
    MISSING_DOCUMENT_CLEARANCE = "missing_document_clearance"
    DEPARTMENT_MISMATCH = "department_mismatch"
    CLEARANCE_INSUFFICIENT = "clearance_insufficient"
    ALLOWED = "allowed"


def decide(user: User, document: Document) -> AccessResult:
    """
    V1 access decision. Pure function.

    Authorization is department plus clearance only.
    `role` does not participate.

    Rule:
        access = (
            user.department == document.department
            OR
            document.department == "ALL"
        )
        AND
        (
            user.clearance >= document.required_clearance
        )
    """
    # 1) Validate inputs. Fail closed with explicit reason codes.
    if not _has_text(user.department):
        return (False, Reason.MISSING_USER_DEPARTMENT)
    if not _has_text(document.department):
        return (False, Reason.MISSING_DOCUMENT_DEPARTMENT)
    if not _is_clearance(user.clearance):
        return (False, Reason.MISSING_USER_CLEARANCE)
    if not _is_clearance(document.required_clearance):
        return (False, Reason.MISSING_DOCUMENT_CLEARANCE)

    # 2) Department check (ALL acts as wildcard).
    department_ok = (
        user.department == document.department
        or document.department == "ALL"
    )
    if not department_ok:
        return (False, Reason.DEPARTMENT_MISMATCH)

    # 3) Clearance check (>=).
    if not user.clearance.is_at_least(document.required_clearance):
        return (False, Reason.CLEARANCE_INSUFFICIENT)

    return (True, Reason.ALLOWED)


def _has_text(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def _is_clearance(value) -> bool:
    return isinstance(value, Clearance)
