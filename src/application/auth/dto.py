"""Data transfer objects for the M5 auth use case.

- `VerifyJwtTokenCommand`: input to `VerifyJwtToken`.
- `AuthActor`: typed projection of the verified JWT for
  downstream consumers (M6+). Holds
  `{user_id, department, clearance, role, correlation_id}`.
- `UNKNOWN_USER_ACTOR`: the typed failure carrier. The docstring
  describes how it threads through `VerifyJwtToken` when
  identity cannot be established: the application surface
  reports it via metadata so the audit row is identifiable as
  "unknown-user-carried" while the underlying
  `actor_user_id: Optional[int]` stays the schema-shaped
  anonymous path (M0's `actor_user_id=None`).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerifyJwtTokenCommand:
    """Input for `VerifyJwtToken`."""

    token: str
    correlation_id: str


@dataclass(frozen=True)
class AuthActor:
    """Typed projection of the authenticated caller.

    Downstream layers (LangGraph state at M6+) consume this
    directly. The `user_id` is the JWT `sub` claim verbatim;
    the middleware trusts the issuer-validated claim and does
    not perform a database lookup at auth time (D-040 Q1).
    """

    user_id: str       # JWT `sub`
    department: str    # JWT `department` claim
    clearance: str     # JWT `clearance` claim
    role: str          # JWT `role` claim
    correlation_id: str


#: The unknown-user failure carrier. D-040 Q2: when authentication
#: fails, the audit row is written with `actor_user_id=None`
#: (anonymous actor — same shape as M0's `actor_user_id is None`)
#: and stamped with
#: `metadata={"auth_failure_carrier": "unknown-user"}` so
#: downstream consumers can identify failure rows without
#: silently inventing a database row. The untyped constants on
#: this module are the canonical "auth says identity is not
#: established" projection; the integers below are deliberately
#: cast to `0` so the typed Python-side string remains
#: literature while the database row stays schema-correct.
UNKNOWN_USER_CARRIER_METADATA_TAG = "auth_failure_carrier"
UNKNOWN_USER_CARRIER_METADATA_VALUE = "unknown-user"

UNKNOWN_USER_ACTOR: AuthActor = AuthActor(
    user_id="unknown-user",
    department="unknown",
    clearance="unknown",
    role="unknown",
    correlation_id="",
)


__all__ = [
    "AuthActor",
    "UNKNOWN_USER_ACTOR",
    "UNKNOWN_USER_CARRIER_METADATA_TAG",
    "UNKNOWN_USER_CARRIER_METADATA_VALUE",
    "VerifyJwtTokenCommand",
]
