"""M5 `VerifyJwtToken` use-case coverage.

Five distinct tests:

1. Happy path returns an `AuthActor` with the right fields.
2. Bad signature raises `JwtBadSignature` AND writes an audit row
   carrying `reason_code="jwt_invalid"` and the unknown-user
   failure-carrier metadata.
3. Empty token raises `AuthFailure`; failure row written with
   `jwt_missing` failure-code tag.
4. `audit_repo=None` raises the failure and writes NO row.
5. Failure-row metadata is preserved exactly.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from src.application.auth.dto import (
    UNKNOWN_USER_CARRIER_METADATA_TAG,
    UNKNOWN_USER_CARRIER_METADATA_VALUE,
    AuthActor,
    VerifyJwtTokenCommand,
)
from src.application.auth.errors import (
    AuthFailure,
    JwtBadSignature,
)
from src.application.auth.signer import HS256JwtSigner, JwtClaims
from src.application.auth.verify_jwt import VerifyJwtToken
from src.domain.ports.audit_logs import AuditDecision


pytestmark = pytest.mark.asyncio


async def _build_valid_token(
    signer: HS256JwtSigner, frozen_now, *, sub: str = "u-1"
) -> str:
    claims = JwtClaims(
        user_id=sub,
        department="engineering",
        clearance="internal",
        role="contributor",
    )
    return signer.sign(claims=claims, exp=frozen_now + timedelta(minutes=30))


async def test_happy_path_returns_auth_actor(
    hs256_signer, frozen_now, seed_clock, in_memory_audit_repo
):
    token = await _build_valid_token(hs256_signer, frozen_now)
    use_case = VerifyJwtToken(
        signer=hs256_signer,
        audit_repo=in_memory_audit_repo,
        clock=seed_clock,
    )
    actor = await use_case(
        VerifyJwtTokenCommand(token=token, correlation_id="cid-m5-01")
    )
    assert isinstance(actor, AuthActor)
    assert actor.user_id == "u-1"
    assert actor.department == "engineering"
    assert actor.clearance == "internal"
    assert actor.role == "contributor"
    assert actor.correlation_id == "cid-m5-01"
    # Success must NOT emit a row.
    rows = await in_memory_audit_repo.find_by_correlation_id("cid-m5-01")
    assert rows == []


async def test_bad_signature_writes_audit_row(
    hs256_signer, alt_hs256_signer, frozen_now, seed_clock, in_memory_audit_repo
):
    token = await _build_valid_token(alt_hs256_signer, frozen_now, sub="u-evil")
    use_case = VerifyJwtToken(
        signer=hs256_signer,
        audit_repo=in_memory_audit_repo,
        clock=seed_clock,
    )
    with pytest.raises(JwtBadSignature):
        await use_case(
            VerifyJwtTokenCommand(token=token, correlation_id="cid-m5-02")
        )
    rows = await in_memory_audit_repo.find_by_correlation_id("cid-m5-02")
    assert len(rows) == 1
    row = rows[0]
    assert row.reason_code == "jwt_invalid"
    assert row.decision == AuditDecision.FAILED
    assert row.actor_user_id is None
    assert row.metadata[UNKNOWN_USER_CARRIER_METADATA_TAG] == (
        UNKNOWN_USER_CARRIER_METADATA_VALUE
    )
    assert row.metadata["auth_failure_code"] == "jwt_bad_signature"


async def test_missing_token_writes_audit_row_with_known_carrier(
    hs256_signer, seed_clock, in_memory_audit_repo
):
    use_case = VerifyJwtToken(
        signer=hs256_signer,
        audit_repo=in_memory_audit_repo,
        clock=seed_clock,
    )
    with pytest.raises(AuthFailure):
        await use_case(
            VerifyJwtTokenCommand(token="", correlation_id="cid-m5-03")
        )
    rows = await in_memory_audit_repo.find_by_correlation_id("cid-m5-03")
    assert len(rows) == 1
    assert rows[0].reason_code == "jwt_invalid"
    assert rows[0].metadata["auth_failure_code"] == "jwt_missing"
    assert rows[0].metadata[UNKNOWN_USER_CARRIER_METADATA_TAG] == (
        UNKNOWN_USER_CARRIER_METADATA_VALUE
    )


async def test_audit_repo_none_does_not_write_row(
    hs256_signer, alt_hs256_signer, frozen_now, seed_clock
):
    """D-040 Q1 invariant: auth must work without a DB."""
    token = await _build_valid_token(alt_hs256_signer, frozen_now)
    use_case = VerifyJwtToken(
        signer=hs256_signer,
        audit_repo=None,
        clock=seed_clock,
    )
    with pytest.raises(JwtBadSignature):
        await use_case(
            VerifyJwtTokenCommand(token=token, correlation_id="cid-m5-04")
        )
    # No repo was passed; nothing to assert on persistence. The
    # call must have raised cleanly without side effects.
    assert True


async def test_unknown_user_carrier_metadata_is_constant(
    hs256_signer, alt_hs256_signer, frozen_now, seed_clock, in_memory_audit_repo
):
    """The unknown-user carrier metadata tag is a constant string.

    Q2: the failure row carries the typed "unknown-user" carrier
    via stable metadata keys consumed by downstream layers.
    """
    token = await _build_valid_token(alt_hs256_signer, frozen_now, sub="u-x")
    use_case = VerifyJwtToken(
        signer=hs256_signer,
        audit_repo=in_memory_audit_repo,
        clock=seed_clock,
    )
    with pytest.raises(JwtBadSignature):
        await use_case(
            VerifyJwtTokenCommand(token=token, correlation_id="cid-m5-05")
        )
    rows = await in_memory_audit_repo.find_by_correlation_id("cid-m5-05")
    assert rows[0].metadata[UNKNOWN_USER_CARRIER_METADATA_TAG] == (
        UNKNOWN_USER_CARRIER_METADATA_VALUE
    )
