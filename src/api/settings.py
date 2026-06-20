"""Runtime settings for the M3 API skeleton.

Settings are read from environment variables prefixed with
`SAGEWELL_`. M3 ships exactly the four fields the skeleton needs:

* `SAGEWELL_LOG_LEVEL` (default `INFO`)
* `SAGEWELL_API_HOST`  (default `127.0.0.1`)
* `SAGEWELL_API_PORT`  (default `8000`)

The settings module intentionally does NOT load
`SAGEWELL_DB_URL`, JWT, CORS, or proxy settings; those belong
to later milestones.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API skeleton runtime configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SAGEWELL_",
        env_file=None,
        case_sensitive=False,
        extra="ignore",
    )

    log_level: str = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = 8000


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton settings object."""
    return Settings()
