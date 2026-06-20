"""Health response schema for `GET /health`."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Fixed shape for `/health`."""

    status: Literal["ok"]
