"""Error response schemas for the M3 API skeleton.

The error envelope is fixed:

    { code, message, correlation_id }

`code` is a stable slug (e.g., `validation_error`,
`internal_error`). `message` is the human-readable summary.
`correlation_id` is the request's `X-Correlation-ID` (echoed or
generated). This shape is the canonical contract for any error
returned by the V1 API; future milestones MUST keep the three
fields.
"""
from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Canonical V1 API error envelope."""

    code: str
    message: str
    correlation_id: str
