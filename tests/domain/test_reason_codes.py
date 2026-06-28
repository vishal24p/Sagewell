"""Domain-port reason-code allow-list canonical tests.

The repository + application layers both gate writes on the same
business rule: every persisted `reason_code` must come from the V1
allow-list. This module locks the canonical set owned by
`src.domain.ports.reason_codes` so any future contradiction between
the in-memory and Postgres adapters, or between the application-layer
validator and the repository-layer validator, is caught here.

Failure of any test below signals that `ALLOWED_REASON_CODES` is no
longer the single source of truth — likely the result of a half-finished
refactor. Do not patch the test; restore the canonical owner.
"""

from __future__ import annotations

import pytest

from src.domain.ports.reason_codes import (
    ALLOWED_REASON_CODES,
    assert_is_allowed_reason_code,
    is_allowed_reason_code,
)


def test_allowed_reason_codes_is_public_exported():
    """The canonical allow-list must be importable as a public name."""
    assert isinstance(ALLOWED_REASON_CODES, frozenset)
    # M0 imm codes are present.
    m0_codes = {
        "allowed",
        "missing_user_department",
        "missing_user_clearance",
        "missing_document_department",
        "missing_document_clearance",
        "department_mismatch",
        "clearance_insufficient",
    }
    assert m0_codes <= ALLOWED_REASON_CODES
    # M5 (JWT), M7 (ingestion), M10 (regex guard), M11 (LLM guard) — all present.
    for code in (
        "jwt_invalid",
        "ingestion_succeeded",
        "ingestion_skipped",
        "ingestion_failed",
        "regex_passed",
        "regex_refused_high",
        "regex_refused_critical",
        "llm_guard_allow",
        "llm_guard_downgrade",
        "llm_guard_refuse",
    ):
        assert code in ALLOWED_REASON_CODES, code


def test_assert_form_raises_value_error_for_unknown_code():
    """The assertion form is the new contract for application-layer checks."""
    with pytest.raises(ValueError) as excinfo:
        assert_is_allowed_reason_code("definitely_not_a_real_code_xyz")
    assert "definitely_not_a_real_code_xyz" in str(excinfo.value)


def test_assert_form_does_not_raise_for_known_codes():
    """Sanity: known codes return without error."""
    for code in ("allowed", "jwt_invalid", "ingestion_succeeded"):
        assert_is_allowed_reason_code(code)


def test_is_allowed_reason_code_predicate_matches_set():
    """The predicate and the set are consistent: every code in the set is allowed."""
    for code in ALLOWED_REASON_CODES:
        assert is_allowed_reason_code(code) is True
    # And a code that's not in the set is rejected.
    assert is_allowed_reason_code("definitely_not_a_real_code_xyz") is False
