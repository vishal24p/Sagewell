"""JWT signer Protocol and the HS256 implementation.

The signer is the single signing/verification boundary at the
application layer. It is independent of the use case
(`VerifyJwtToken`) so that future milestones can swap the
algorithm (RS256, EdDSA) without touching the rest of the
application package.

Boundary:

- Reads claims (subject/department/clearance/role) and `exp`
  (a `datetime`) on sign.
- Returns `JwtClaims` on verify; raises the typed
  `AuthFailure` subclasses from `errors.py` on failure.
- Pure: no DB, no clock externally injected (the use case
  passes `now` into `verify`).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import NamedTuple, Protocol

import jwt as pyjwt  # PyJWT

from src.application.auth.errors import (
    JwtBadSignature,
    JwtExpired,
    JwtInvalid,
    JwtMalformed,
)


# Expected JWT claims. M5 ships the canonical four-business-claim
# set: subject, department, clearance, role. The HS256 implementation
# also reads the standard `exp` claim from PyJWT's decoding layer.
_REQUIRED_CLAIMS: tuple[str, ...] = ("sub", "department", "clearance", "role")


class JwtClaims(NamedTuple):
    """Verified JWT claim bundle. Mirrors the typed `AuthActor` minus `correlation_id`."""

    user_id: str       # `sub`
    department: str    # `department`
    clearance: str     # `clearance`
    role: str          # `role`


class JwtSigner(Protocol):
    """Application-layer JWT signing/verification boundary."""

    def sign(self, *, claims: JwtClaims, exp: datetime) -> str: ...

    def verify(self, token: str, *, now: datetime) -> JwtClaims: ...


class HS256JwtSigner:
    """HS256-only signer and verifier.

    The constructor accepts the shared secret as `bytes` so
    that secret material never lives in the application layer
    as a Python string. A 5-second clock leeway is anchored
    per JWT spec to absorb small clock skew across hosts.
    """

    ALGORITHM: str = "HS256"

    def __init__(
        self,
        *,
        secret: bytes,
        leeway_seconds: int = 5,
    ) -> None:
        if not isinstance(secret, (bytes, bytearray)):
            raise TypeError("HS256JwtSigner requires a bytes secret")
        if leeway_seconds < 0:
            raise ValueError("leeway_seconds must be non-negative")
        self._secret = bytes(secret)
        self._leeway_seconds = int(leeway_seconds)

    def sign(self, *, claims: JwtClaims, exp: datetime) -> str:
        payload = {
            "sub": claims.user_id,
            "department": claims.department,
            "clearance": claims.clearance,
            "role": claims.role,
            "exp": int(exp.timestamp()),
        }
        # PyJWT 2.x returns a str on encode. Plain `str` is the
        # canonical JWT wire format; do NOT encode to bytes.
        return pyjwt.encode(payload, self._secret, algorithm=self.ALGORITHM)

    def verify(self, token: str, *, now: datetime) -> JwtClaims:
        if not isinstance(token, str) or not token:
            raise JwtMalformed("token is empty")
        try:
            # PyJWT does not accept a caller-supplied `now`, so we
            # disable its built-in `exp` validation and verify
            # `exp` ourselves using the use case's `Clock`. The
            # signature is still verified by PyJWT against the
            # configured secret.
            payload = pyjwt.decode(
                token,
                self._secret,
                algorithms=[self.ALGORITHM],
                leeway=self._leeway_seconds,
                options={
                    "require": list(_REQUIRED_CLAIMS),
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_nbf": False,
                },
            )
        except pyjwt.InvalidSignatureError as exc:
            raise JwtBadSignature("signature did not verify") from exc
        except pyjwt.MissingRequiredClaimError as exc:
            raise JwtInvalid(
                f"required claim missing: {getattr(exc, 'claim', 'unknown')}"
            ) from exc
        except pyjwt.DecodeError as exc:
            raise JwtMalformed("token could not be decoded") from exc

        # Manual `exp` validation against the use-case-supplied
        # `now` (with the configured leeway). This keeps the
        # signing/verification boundary testable against a
        # frozen clock and avoids any reliance on the
        # process' wall-clock time.
        exp = payload.get("exp")
        if not isinstance(exp, (int, float)):
            raise JwtInvalid("exp claim missing or not numeric")
        try:
            exp_dt = datetime.fromtimestamp(float(exp), tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as exc:
            raise JwtInvalid("exp claim out of range") from exc
        if exp_dt < now - timedelta(seconds=self._leeway_seconds):
            raise JwtExpired("token has expired")

        try:
            return JwtClaims(
                user_id=str(payload["sub"]),
                department=str(payload["department"]),
                clearance=str(payload["clearance"]),
                role=str(payload["role"]),
            )
        except KeyError as exc:
            raise JwtInvalid("required claim missing") from exc


__all__ = ["HS256JwtSigner", "JwtClaims", "JwtSigner"]
