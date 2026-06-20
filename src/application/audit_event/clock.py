"""Clock Protocol for the audit intake use case.

The use case stamps `created_at` from a `Clock` so tests can
freeze the timestamp. Production code wires `SystemClock()`
when the use case enters runtime at M5+; nothing in M4
constructs a clock implicitly.

The Protocol lives in this layer because the use case owns the
stamping. No asyncpg, no framework imports.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    """Returns the current timestamp as a `datetime`."""

    def now(self) -> datetime: ...


class SystemClock:
    """Production `Clock`. Returns UTC `datetime.now()`."""

    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)


__all__ = ["Clock", "SystemClock"]
