"""`VerifyJwtToken` use case.

Async use case. Single application-layer entry point for JWT
validation.

On success the use case returns the typed `AuthActor`. On any
`AuthFailure` the use case:

  1. If `audit_repo` is provided, awaits a `RecordAuditEvent`
     write carrying `reason_code="jwt_invalid"` and the
     unknown-user failure-carrier metadata (the DB-free launch
     keeps `audit_repo=None` and skips this step; the failure
     still raises).
  2. Re-raises the typed `AuthFailure` so the API middleware
     can translate to the canonical 401 envelope.

Boundary:

- Imports from `src/domain/ports/` and intra-application.
- Does NOT import from `src/api/`, `src/infrastructure/`, or
  any framework SDK.
- Trusts the JWT per D-040 Q1 (no DB lookup); this use case is
  the canonical place to perform any future issuer-trust-model
  change.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from src.application.audit_event.clock import Clock, SystemClock
from src.application.audit_event.dto import RecordAuditCommand
from src.application.audit_event.record import RecordAuditEvent
from src.application.auth.dto import (
    AuthActor,
    UNKNOWN_USER_CARRIER_METADATA_TAG,
    UNKNOWN_USER_CARRIER_METADATA_VALUE,
    VerifyJwtTokenCommand,
)
from src.application.auth.errors import AuthFailure
from src.application.auth.signer import JwtSigner
from src.domain.ports.audit_logs import (
    AuditDecision,
    AuditLogRepository,
)


_logger = logging.getLogger("sagewell.application.auth")


class VerifyJwtToken:
    """Application-layer use case. Verifies an HS256 JWT and projects an `AuthActor`.

    Construction takes:

    - `signer`: the application's verified-signing boundary.
    - `audit_repo`: optional. When supplied, every failure
      produces an audit row (best-effort); when None the use
      case still raises, but no row is written (DB-free launch
      preserves M3 behaviour for tests/dev).
    - `clock`: optional injected time source. Defaults to
      `SystemClock()` when not provided. Production callers
      pass nothing; tests inject a frozen clock for deterministic
      `exp` math.
    """

    def __init__(
        self,
        *,
        signer: JwtSigner,
        audit_repo: Optional[AuditLogRepository],
        clock: Optional[Clock] = None,
    ) -> None:
        self._signer = signer
        self._audit_repo = audit_repo
        self._clock: Clock = clock if clock is not None else SystemClock()

    async def __call__(self, command: VerifyJwtTokenCommand) -> AuthActor:
        if not isinstance(command.token, str) or not command.token:
            await self._record_failure(
                correlation_id=command.correlation_id, code="jwt_missing"
            )
            raise AuthFailure("token is missing")

        now: datetime = self._clock.now()
        try:
            claims = self._signer.verify(command.token, now=now)
        except AuthFailure as exc:
            await self._record_failure(
                correlation_id=command.correlation_id, code=exc.code
            )
            raise

        return AuthActor(
            user_id=claims.user_id,
            department=claims.department,
            clearance=claims.clearance,
            role=claims.role,
            correlation_id=command.correlation_id,
        )

    async def _record_failure(
        self, *, correlation_id: str, code: str
    ) -> None:
        """Best-effort write of the JWT failure audit row.

        Persistence failures are logged at WARNING and never
        raised — the auth failure is the canonical user-visible
        error. When `audit_repo is None` the method is a no-op.
        """
        if self._audit_repo is None:
            return
        writer = RecordAuditEvent(self._audit_repo, clock=self._clock)
        cmd = RecordAuditCommand(
            actor_user_id=None,
            action="auth.jwt.evaluated",
            resource_type=None,
            resource_id=None,
            decision=AuditDecision.FAILED,
            reason_code="jwt_invalid",
            correlation_id=correlation_id,
            metadata={
                UNKNOWN_USER_CARRIER_METADATA_TAG: (
                    UNKNOWN_USER_CARRIER_METADATA_VALUE
                ),
                "auth_failure_code": code,
            },
        )
        try:
            await writer(cmd)
        except Exception as exc:  # noqa: BLE001 - intentional log-only
            _logger.warning(
                "verify_jwt.audit_write_failed",
                extra={
                    "correlation_id": correlation_id,
                    "exception_type": type(exc).__name__,
                    "exc_message": str(exc),
                },
            )


__all__ = ["VerifyJwtToken"]
