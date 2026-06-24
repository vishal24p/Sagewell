"""Runtime settings for the V1 API.

Settings are read from environment variables prefixed with
`SAGEWELL_`. M3 ships:

* `SAGEWELL_LOG_LEVEL` (default `INFO`)
* `SAGEWELL_API_HOST`  (default `127.0.0.1`)
* `SAGEWELL_API_PORT`  (default `8000`)

M5 adds:

* `SAGEWELL_JWT_SECRET` (no default; required only when the
   auth middleware is enabled at runtime). When unset, the
   API launches in M3-style passthrough mode and ignores
   auth on every route.

The settings module intentionally does NOT load
`SAGEWELL_DB_URL`, CORS, or proxy settings; those belong
to later milestones.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API runtime configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SAGEWELL_",
        env_file=None,
        case_sensitive=False,
        extra="ignore",
    )

    log_level: str = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # M5: optional HS256 shared secret. Required at runtime only
    # when the auth middleware is enabled (i.e., when
    # `__main__.py` constructs an `HS256JwtSigner`).
    jwt_secret: Optional[bytes] = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton settings object."""
    return Settings()
