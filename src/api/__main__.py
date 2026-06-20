"""Run the M3 API skeleton via `python -m src.api`.

Equivalent to:

    uvicorn src.api.app:create_app --factory

`SAGEWELL_API_HOST` / `SAGEWELL_API_PORT` configure the listen
address. Override with CLI args if required.
"""
from __future__ import annotations

import uvicorn

from src.api.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "src.api.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
