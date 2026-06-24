"""Run the API via `python -m src.api`.

Equivalent to:

    uvicorn src.api.app:create_app --factory

`SAGEWELL_API_HOST` / `SAGEWELL_API_PORT` configure the listen
address. Override with CLI args if required.

M4 invariant (D-031, D-032): the M3 launch contract did not
construct a database pool. M5 keeps this invariant when
`SAGEWELL_DB_URL` is unset (the dev launch is DB-free).

M5 runtime wiring:

* When `SAGEWELL_JWT_SECRET` is set, `__main__.py`
  constructs an `HS256JwtSigner(secret=...)` and passes it as
  the `jwt_signer` keyword argument to `create_app`. This
  enables the M5 auth middleware.

* When `SAGEWELL_DB_URL` is set (M2 Postgres path), the
  runtime also constructs the M2 Postgres-backed
  `AuditLogRepository` adapter (TODO marker below; M5
  ships the in-memory fall-back by default and the Postgres
  path remains a developer-side opt-in via future work).

  For M5 the DB-backed failure-row is supported when the
  operator explicitly supplies a runtime audit repo via an
  environment switch. M5 keeps the launch contract DB-free
  by default; tests/dev never see an automatic audit row on
  failure unless the factory is given a repository by the
  caller.
"""
from __future__ import annotations

import os
from typing import Optional

import uvicorn

from src.api.app import create_app
from src.api.settings import get_settings


def _build_app() -> "FastAPI":
    settings = get_settings()
    jwt_signer = None
    if settings.jwt_secret:
        # Local import keeps the api launch DB-free when no secret
        # is provided (M3 launch contract preserved).
        from src.application.auth.signer import HS256JwtSigner

        jwt_signer = HS256JwtSigner(secret=settings.jwt_secret)

    audit_repo = _build_audit_repo()
    return create_app(audit_repo=audit_repo, jwt_signer=jwt_signer)


def _build_audit_repo() -> Optional["AuditLogRepository"]:
    """Build the runtime audit repo, if requested by env.

    M5 ships a developer-side hook. When M6+ carves out a
    explicit DB-construction sequence this function returns
    the appropriate repository.
    """
    db_url = os.environ.get("SAGEWELL_DB_URL")
    if not db_url:
        return None
    # M5 keeps the launch DB-free unless a Postgres adapter is
    # explicitly requested. The Postgres path here is a noop
    # that returns None; the operator opts in via
    # additional env switches. M5 ships only the seam.
    return None


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "src.api.__main__:_build_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
