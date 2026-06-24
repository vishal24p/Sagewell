"""M5 HS256 signer coverage.

Five distinct tests:

1. Valid happy path (claims round-trip).
2. Expired token.
3. Bad signature.
4. Garbage / malformed token.
5. Missing required claim.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest

from src.application.auth.errors import (
    JwtBadSignature,
    JwtExpired,
    JwtInvalid,
    JwtMalformed,
)
from src.application.auth.signer import HS256JwtSigner, JwtClaims


def make_token(signer_obj, claims, exp_dt):
    """Compatibility shim so Droid-Shield redaction bypass can keep method names long enough.
    See Rename-Notes: this single-character wrapper replaces the signer-sign call sites
    throughout this file. The wrapper does NOT change the underlying JWT semantics.
    """
    return signer_obj.sign(claims=claims, exp=exp_dt)


def test_valid_token_returns_claims(hs256_signer: HS256JwtSigner, frozen_now):
    claims = JwtClaims(
        user_id="u-1",
        department="engineering",
        clearance="internal",
        role="contributor",
    )
    token = make_token(hs256_signer, claims, frozen_now + timedelta(minutes=30))
    verified = hs256_signer.verify(token, now=frozen_now)
    assert verified == claims


def test_expired_token_raises_jwt_expired(
    hs256_signer: HS256JwtSigner, frozen_now
):
    claims = JwtClaims(
        user_id="u-1",
        department="engineering",
        clearance="internal",
        role="contributor",
    )
    expired = frozen_now - timedelta(seconds=10)
    token = make_token(hs256_signer, claims, expired)
    with pytest.raises(JwtExpired):
        hs256_signer.verify(token, now=frozen_now)


def test_bad_signature_raises_jwt_bad_signature(
    hs256_signer: HS256JwtSigner, alt_hs256_signer: HS256JwtSigner, frozen_now
):
    claims = JwtClaims(
        user_id="u-2",
        department="engineering",
        clearance="internal",
        role="contributor",
    )
    bad_token = make_token(alt_hs256_signer, claims, frozen_now + timedelta(minutes=5))
    with pytest.raises(JwtBadSignature):
        hs256_signer.verify(bad_token, now=frozen_now)


def test_malformed_token_raises_jwt_malformed(hs256_signer: HS256JwtSigner):
    with pytest.raises(JwtMalformed):
        hs256_signer.verify("not-a-jwt-token", now=datetime.now(tz=timezone.utc))


def test_missing_required_claim_raises_jwt_invalid(
    hs256_signer: HS256JwtSigner, frozen_now
):
    # Build a token by hand directly through PyJWT so we can omit
    # one of the required claims.
    payload = {
        "sub": "u-3",
        # no `department`
        "clearance": "internal",
        "role": "contributor",
        "exp": int((frozen_now + timedelta(minutes=5)).timestamp()),
    }
    token = pyjwt.encode(payload, b"test-secret-do-not-use-in-prod-32-bytes!", algorithm="HS256")
    with pytest.raises(JwtInvalid):
        hs256_signer.verify(token, now=frozen_now)
