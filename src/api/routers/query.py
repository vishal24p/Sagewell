"""M9 `/v1/query` route.

The route is the API boundary to the M9 LangGraph
workflow (and its M8 retrieval + M9 citation-
verification nodes). The handler:

  1. Reads the verified `AuthActor` from the request's
     ASGI state (placed there by the M5 JWT middleware).
  2. Builds a typed `WorkflowState` via
     `WorkflowState.from_actor(actor, query=...)`.
  3. Calls `app.state.run_query(state)` -- a function
     placed on `app.state` by the DI seam in
     `app.create_app(...)`. The function orchestrates
     the retrieval + citation-verification pipeline.
  4. Translates the typed result into the
     canonical JSON envelope.

The route never assumes a real DB / real embedding
model. When `run_query is None` (the launch contract
on `uvicorn src.api.app:create_app --factory`
without DI) the handler returns a 503 typed error.

D-028 forward-hook: the route layer imports the
workflow package (it is the inner-binding callback),
never the other way around.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.errors.schemas import ErrorResponse
from src.application.auth.dto import AuthActor
from src.application.workflow.errors import AnonymousExecutionError
from src.application.workflow.state import WorkflowState


router = APIRouter()


def _actor_or_none(request: Request) -> Optional[AuthActor]:
    """Return the verified `AuthActor` from ASGI state if any.

    The M5 JWT middleware has placed the typed actor on
    `scope["state"]["actor"]` for any request that has
    passed verification. This helper does NOT raise; a
    missing actor becomes `None` and the handler
    translates that into a 401.
    """
    state = getattr(request, "state", None)
    if state is None:
        return None
    return getattr(state, "actor", None)


@router.post(
    "/v1/query",
    summary="Run the V1 retrieval + citation-verification pipeline.",
)
async def query_handler(request: Request) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "")

    actor: Optional[AuthActor] = _actor_or_none(request)
    if actor is None:
        env = ErrorResponse(
            code="unauthorized",
            message="JWT verification required; missing or invalid actor.",
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=401,
            content=env.model_dump(),
        )

    body = await request.json()
    query_text = (body or {}).get("query") or ""
    if not query_text.strip():
        env = ErrorResponse(
            code="validation_error",
            message="`query` is required and must be non-blank.",
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=400,
            content=env.model_dump(),
        )

    run_query = getattr(request.app.state, "run_query", None)
    if run_query is None:
        env = ErrorResponse(
            code="service_unavailable",
            message=(
                "M9 retrieval + citation verification are not wired on this app; "
                "pass run_query=<callable> through create_app(...)."
            ),
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=503,
            content=env.model_dump(),
        )

    try:
        state = WorkflowState.from_actor(actor, query=query_text)
    except AnonymousExecutionError as exc:
        env = ErrorResponse(
            code="unauthorized",
            message=str(exc),
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=401,
            content=env.model_dump(),
        )

    result = await run_query(state)
    return JSONResponse(
        status_code=200,
        content=result,
    )


__all__ = ["router", "query_handler"]
