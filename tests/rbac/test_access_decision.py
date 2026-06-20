"""
RBAC Access Outcome Suite for M0.

Plain, table-driven unit tests validating the pure access-decision
function. No framework. No database. No network.

Coverage categories:
    - Allow Tests
    - Deny Tests
    - Department Tests (boundary, ALL wildcard)
    - Clearance Tests (boundary, insufficient, equal)
    - Missing-fields Tests (fail-closed)
    - Role regression Test (role MUST NOT influence authorization)

The suite asserts access-decision outcomes (allowed, reason),
not answer strings.
"""
import pytest

from src.domain.access.access_decision import Reason, decide
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentProjection as Document
from src.domain.ports.users import UserProjection as User


# Sample departments used across cases.
DEPT_FIN = "finance"
DEPT_HR = "hr"
DEPT_ENG = "engineering"


# ---------------------------------------------------------------------------
# Allow Tests
# Same department + sufficient clearance yields allow.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "user, document",
    [
        # Same department, equal clearance (boundary).
        (
            User(department=DEPT_FIN, clearance=Clearance.PUBLIC),
            Document(department=DEPT_FIN, required_clearance=Clearance.PUBLIC),
        ),
        # Same department, clearance strictly greater.
        (
            User(department=DEPT_FIN, clearance=Clearance.CONFIDENTIAL),
            Document(department=DEPT_FIN, required_clearance=Clearance.INTERNAL),
        ),
        # Same department, top clearance.
        (
            User(department=DEPT_HR, clearance=Clearance.RESTRICTED),
            Document(department=DEPT_HR, required_clearance=Clearance.CONFIDENTIAL),
        ),
        # ALL document, sufficient clearance from any department.
        (
            User(department=DEPT_ENG, clearance=Clearance.INTERNAL),
            Document(department="ALL", required_clearance=Clearance.INTERNAL),
        ),
    ],
)
def test_allow_cases(user, document):
    allowed, reason = decide(user, document)
    assert allowed is True
    assert reason == Reason.ALLOWED


# ---------------------------------------------------------------------------
# Deny Tests (positive deny)
# Confirmed-deny paths with explicit reason codes.
# ---------------------------------------------------------------------------
def test_deny_department_mismatch():
    user = User(department=DEPT_FIN, clearance=Clearance.RESTRICTED)
    doc = Document(department=DEPT_HR, required_clearance=Clearance.PUBLIC)

    allowed, reason = decide(user, doc)

    assert allowed is False
    assert reason == Reason.DEPARTMENT_MISMATCH


def test_deny_clearance_insufficient():
    user = User(department=DEPT_FIN, clearance=Clearance.INTERNAL)
    doc = Document(department=DEPT_FIN, required_clearance=Clearance.CONFIDENTIAL)

    allowed, reason = decide(user, doc)

    assert allowed is False
    assert reason == Reason.CLEARANCE_INSUFFICIENT


def test_deny_both_fail_returns_department_first():
    # Department mismatch is checked before clearance.
    user = User(department=DEPT_FIN, clearance=Clearance.PUBLIC)
    doc = Document(department=DEPT_HR, required_clearance=Clearance.CONFIDENTIAL)

    allowed, reason = decide(user, doc)

    assert allowed is False
    assert reason == Reason.DEPARTMENT_MISMATCH


# ---------------------------------------------------------------------------
# Department Tests
# - Department boundary: same department required.
# - ALL wildcard: works from any actor department.
# - Different actor departments against the same document produce deny.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "other_dept",
    [DEPT_HR, DEPT_ENG, "marketing"],
)
def test_same_document_denies_actors_from_other_departments(other_dept):
    document = Document(department=DEPT_FIN, required_clearance=Clearance.PUBLIC)
    other_actor = User(department=other_dept, clearance=Clearance.RESTRICTED)

    allowed, reason = decide(other_actor, document)

    assert allowed is False
    assert reason == Reason.DEPARTMENT_MISMATCH


def test_all_document_allows_any_department_when_clearance_satisfied():
    document = Document(department="ALL", required_clearance=Clearance.PUBLIC)

    actors = [
        User(department=DEPT_FIN, clearance=Clearance.PUBLIC),
        User(department=DEPT_HR, clearance=Clearance.INTERNAL),
        User(department=DEPT_ENG, clearance=Clearance.CONFIDENTIAL),
    ]

    for actor in actors:
        allowed, reason = decide(actor, document)
        assert allowed is True
        assert reason == Reason.ALLOWED


def test_all_document_does_not_bypass_clearance():
    document = Document(department="ALL", required_clearance=Clearance.RESTRICTED)
    actor = User(department=DEPT_FIN, clearance=Clearance.INTERNAL)

    allowed, reason = decide(actor, document)

    assert allowed is False
    assert reason == Reason.CLEARANCE_INSUFFICIENT


# ---------------------------------------------------------------------------
# Clearance Tests
# - Equal clearance is allow.
# - Lower clearance denies with CLEARANCE_INSUFFICIENT.
# - Same document across actors with different clearances behaves correctly.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "clearance, expected_allowed",
    [
        (Clearance.PUBLIC, True),
        (Clearance.INTERNAL, True),
        (Clearance.CONFIDENTIAL, True),
        (Clearance.RESTRICTED, True),
    ],
)
def test_equal_or_higher_clearance_allows(clearance, expected_allowed):
    user = User(department=DEPT_FIN, clearance=clearance)
    doc = Document(department=DEPT_FIN, required_clearance=Clearance.PUBLIC)

    allowed, reason = decide(user, doc)

    assert allowed is expected_allowed
    assert reason == Reason.ALLOWED


def test_strictly_lower_clearance_denies():
    user = User(department=DEPT_FIN, clearance=Clearance.PUBLIC)
    doc = Document(department=DEPT_FIN, required_clearance=Clearance.INTERNAL)

    allowed, reason = decide(user, doc)

    assert allowed is False
    assert reason == Reason.CLEARANCE_INSUFFICIENT


def test_same_document_across_clearance_levels():
    document = Document(department=DEPT_FIN, required_clearance=Clearance.CONFIDENTIAL)

    below = User(department=DEPT_FIN, clearance=Clearance.INTERNAL)
    equal = User(department=DEPT_FIN, clearance=Clearance.CONFIDENTIAL)
    above = User(department=DEPT_FIN, clearance=Clearance.RESTRICTED)

    assert decide(below, document) == (False, Reason.CLEARANCE_INSUFFICIENT)
    assert decide(equal, document) == (True, Reason.ALLOWED)
    assert decide(above, document) == (True, Reason.ALLOWED)


# ---------------------------------------------------------------------------
# Missing-fields Tests (fail-closed)
# Any missing authorization input yields DENY with explicit reason code.
# No exceptions are used as authorization outcomes.
# ---------------------------------------------------------------------------
def test_missing_user_department_denies():
    user = User(department=None, clearance=Clearance.PUBLIC)
    doc = Document(department=DEPT_FIN, required_clearance=Clearance.PUBLIC)

    allowed, reason = decide(user, doc)

    assert allowed is False
    assert reason == Reason.MISSING_USER_DEPARTMENT


def test_missing_user_clearance_denies():
    user = User(department=DEPT_FIN, clearance=None)
    doc = Document(department=DEPT_FIN, required_clearance=Clearance.PUBLIC)

    allowed, reason = decide(user, doc)

    assert allowed is False
    assert reason == Reason.MISSING_USER_CLEARANCE


def test_missing_document_department_denies():
    user = User(department=DEPT_FIN, clearance=Clearance.PUBLIC)
    doc = Document(department=None, required_clearance=Clearance.PUBLIC)

    allowed, reason = decide(user, doc)

    assert allowed is False
    assert reason == Reason.MISSING_DOCUMENT_DEPARTMENT


def test_missing_document_required_clearance_denies():
    user = User(department=DEPT_FIN, clearance=Clearance.PUBLIC)
    doc = Document(department=DEPT_FIN, required_clearance=None)

    allowed, reason = decide(user, doc)

    assert allowed is False
    assert reason == Reason.MISSING_DOCUMENT_CLEARANCE


def test_empty_string_department_denies():
    # Empty/whitespace strings are treated as missing.
    user = User(department="   ", clearance=Clearance.PUBLIC)
    doc = Document(department=DEPT_FIN, required_clearance=Clearance.PUBLIC)

    allowed, reason = decide(user, doc)

    assert allowed is False
    assert reason == Reason.MISSING_USER_DEPARTMENT


def test_non_clearance_value_denies():
    # A non-Clearance value for clearance yields MISSING_USER_CLEARANCE.
    user = User(department=DEPT_FIN, clearance="INTERNAL")  # type: ignore[arg-type]
    doc = Document(department=DEPT_FIN, required_clearance=Clearance.PUBLIC)

    allowed, reason = decide(user, doc)

    assert allowed is False
    assert reason == Reason.MISSING_USER_CLEARANCE


# ---------------------------------------------------------------------------
# Role Regression Test
# `role` MUST NOT participate in authorization.
# Identical department and clearance with different roles must produce
# identical access-decision outcomes. This guards against future drift
# (e.g. someone re-introducing role-based authorization by accident).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "role",
    ["employee", "analyst", "manager", "executive", "admin"],
)
def test_role_does_not_influence_authorization_when_dept_and_clearance_fixed(role):
    base_dept = DEPT_FIN
    base_clearance = Clearance.CONFIDENTIAL

    # Two documents exercising allow and deny paths.
    allow_doc = Document(department=base_dept, required_clearance=Clearance.PUBLIC)
    deny_doc = Document(department=DEPT_HR, required_clearance=Clearance.PUBLIC)

    actor_with_role = User(
        department=base_dept, clearance=base_clearance, role=role
    )
    actor_without_role = User(
        department=base_dept, clearance=base_clearance, role=None
    )

    assert decide(actor_with_role, allow_doc) == decide(actor_without_role, allow_doc)
    assert decide(actor_with_role, deny_doc) == decide(actor_without_role, deny_doc)
    assert decide(actor_with_role, allow_doc) == (True, Reason.ALLOWED)
    assert decide(actor_with_role, deny_doc) == (False, Reason.DEPARTMENT_MISMATCH)


def test_role_regression_same_actor_varied_roles_produce_identical_results():
    document = Document(department=DEPT_FIN, required_clearance=Clearance.INTERNAL)
    actor_template = {
        "department": DEPT_FIN,
        "clearance": Clearance.RESTRICTED,
    }

    baseline = decide(
        User(**actor_template, role=None),  # type: ignore[arg-type]
        document,
    )

    for role in ["employee", "analyst", "manager", "executive", "admin"]:
        outcome = decide(
            User(**actor_template, role=role),  # type: ignore[arg-type]
            document,
        )
        assert outcome == baseline


# ---------------------------------------------------------------------------
# All-documents-cleared truth-table sweep.
# Confirms the full cell coverage for (user_clearance × required_clearance)
# at fixed matching department.
# ---------------------------------------------------------------------------
def test_clearance_truth_table_same_department():
    document = Document(department=DEPT_FIN, required_clearance=Clearance.CONFIDENTIAL)

    cases = [
        (Clearance.PUBLIC, False),
        (Clearance.INTERNAL, False),
        (Clearance.CONFIDENTIAL, True),
        (Clearance.RESTRICTED, True),
    ]

    for user_clearance, expected_allowed in cases:
        actor = User(department=DEPT_FIN, clearance=user_clearance)
        allowed, reason = decide(actor, document)
        assert allowed is expected_allowed, (
            f"clearance={user_clearance} expected allowed={expected_allowed}"
        )
        if expected_allowed:
            assert reason == Reason.ALLOWED
        else:
            assert reason == Reason.CLEARANCE_INSUFFICIENT
