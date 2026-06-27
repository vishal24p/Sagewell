"""API surface protocols.

The router at `src/api/routers/query.py` accepts a
`run_query` callable wired through `create_app(...)`. The
function shape is the typed contract the workflow layer
exposes; the API layer depends on this Protocol only.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Protocol

from src.application.workflow.state import WorkflowState


class RunQueryFn(Protocol):
    """Typed callback the workflow layer registers with the API.

    The runtime signature:

        async def run_query(state: WorkflowState) -> dict[str, Any]

    The return payload is the JSON envelope the API
    serializes verbatim. The M9 contract returns:
    `{"query": ..., "correlation_id": ..., "retrieved": [...],
    "citations": [...], "authorization": {"allowed": bool,
    "reason": str}}`.

    The M9 closure ships a real run_query that drives
    LangGraph; the in-memory test wiring provides a stub.
    """

    async def __call__(
        self,
        state: WorkflowState,
    ) -> dict[str, Any]: ...


RunQueryFnType = Callable[[WorkflowState], Awaitable[dict[str, Any]]]


__all__ = ["RunQueryFn", "RunQueryFnType"]
