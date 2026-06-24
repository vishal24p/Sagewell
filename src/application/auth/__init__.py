"""M5 authentication application package.

This package implements identity establishment only:

    - HS256 JWT signing/verification (D-001).
    - A `VerifyJwtToken` use case that projects the verified
      token into a typed `AuthActor`.
    - A typed-failure hierarchy (`AuthFailure` subclasses) that
      distinguishes missing / malformed / bad-signature /
      expired / generic-invalid tokens.

Imports only from `src/domain/ports/` and intra-application. No
fastapi, no pydantic, no asyncpg, no framework SDK. The auth
package itself does NOT call any repository; the middleware
uses the `RecordAuditEvent` use case (M4) to write the failure
row, with `audit_repo: None` meaning "no audit row on failure
(DB-free launch)". Per D-001 the long-term JWT algorithm is
still open pin; M5 is HS256 only.
"""
from src.application.auth.dto import (
    AuthActor,
    UNKNOWN_USER_ACTOR,
    VerifyJwtTokenCommand,
)
from src.application.auth.errors import (
    AuthFailure,
    JwtBadSignature,
    JwtExpired,
    JwtInvalid,
    JwtMalformed,
    JwtMissing,
)
from src.application.auth.signer import (
    HS256JwtSigner,
    JwtClaims,
    JwtSigner,
)
from src.application.auth.verify_jwt import VerifyJwtToken

__all__ = [
    "AuthFailure",
    "AuthActor",
    "HS256JwtSigner",
    "JwtBadSignature",
    "JwtClaims",
    "JwtExpired",
    "JwtInvalid",
    "JwtMalformed",
    "JwtMissing",
    "JwtSigner",
    "UNKNOWN_USER_ACTOR",
    "VerifyJwtToken",
    "VerifyJwtTokenCommand",
]
