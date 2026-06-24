"""Typed-failure hierarchy for token-side authentication failures.

Every subclass carries a stable `.code` slug. The middleware
maps the exception to the canonical 401 envelope and the M5
audit row's `reason_code="jwt_invalid"`. The audit row is
written through M4's `RecordAuditEvent` use case; the auth
package itself does not depend on a repo.

Boundary:

- The packages that consume these failures are
  `src/application/auth/verify_jwt.py` (raises them) and
  `src/api/middleware/auth.py` (catches them and maps to 401).
"""
from __future__ import annotations


class AuthFailure(Exception):
    """Base class for any token-side authentication failure."""

    code: str = "auth_failed"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__


class JwtMissing(AuthFailure):
    """No `Authorization: Bearer ...` header supplied."""

    code: str = "jwt_missing"


class JwtMalformed(AuthFailure):
    """`Authorization` header is malformed (e.g., wrong scheme, empty token)."""

    code: str = "jwt_malformed"


class JwtBadSignature(AuthFailure):
    """JWT signature did not verify against the configured secret."""

    code: str = "jwt_bad_signature"


class JwtExpired(AuthFailure):
    """Token is past its `exp` claim."""

    code: str = "jwt_expired"


class JwtInvalid(AuthFailure):
    """Generic JWT validation failure (missing claim, bad structure, etc.)."""

    code: str = "jwt_invalid"


__all__ = [
    "AuthFailure",
    "JwtBadSignature",
    "JwtExpired",
    "JwtInvalid",
    "JwtMalformed",
    "JwtMissing",
]
