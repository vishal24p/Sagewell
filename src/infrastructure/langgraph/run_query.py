"""M9 -- LangGraph workflow adapter.

The M9 adapter binds the typed `WorkflowState` onto a
LangGraph state machine that captures the V1 retrieval
+ citation-verification pipeline:

  START -> ingest_query
       -> embed -> retrieve_authorized (M8)
       -> verify_citations (M9)
       -> mint_response -> END

The adapter is the only place where `langgraph` is
imported. The application package
(`src/application/workflow/`) is framework-free and
imports the typed `WorkflowState` only.

The retrieval, embedding, citation-verification, and
response-minting use cases are injected through
constructor args. The factory pattern keeps the adapter
testable: tests pass in-memory stubs (the test fixtures
below). Production wiring passes the real M8 dense/BM25
adapters + the M9 verification use case.

`run_query(state)` is the canonical async entry point
the API layer binds onto `app.state.run_query`. The
function:
  1. Builds the LangGraph state machine with the
     injected use cases.
  2. Awaits the async graph result.
  3. Returns the canonical JSON envelope.

The typed `WorkflowState` returned at the end is
unused -- the API layer only sees the JSON envelope.
The state machine is intentionally run-once (not
checkpointed); the V1 production agent is a stateless
request/response endpoint.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Awaitable, Callable, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from src.application.citations.verify import (
    VerifyCitations,
    VerifyCitationsCommand,
)
from src.application.retrieval.retrieve import (
    RetrieveAuthorizedCandidates,
    RetrieveAuthorizedCommand,
)
from src.application.workflow.errors import IncompleteActorError
from src.application.workflow.state import WorkflowState


class _WorkflowChannel(TypedDict, total=False):
    """The M9 channel shape.

    `total=False` makes every field optional **in the
    channel schema only**. The application-layer guarantee
    (no anonymous execution, actor always present) is
    enforced before the channel is built.
    """

    user_id: str
    department: str
    clearance: str
    role: str
    correlation_id: str
    query: str | None
    citations: list  # Citation dicts after the M9 verifier
    authorization: dict  # dict[str, str | bool]


EmbedderFn = Callable[[str], list[float]]
BuildCitationsFn = Callable[
    [WorkflowState, dict[str, Any]],
    Awaitable[list[dict[str, Any]]],
]


async def default_build_citations(
    state: WorkflowState,
    retrieval_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Default citation builder.

    The M9 surface couples an M8 retrieval result with
    the documents-port projection. The default builder
    extracts citations directly from the post-rerank
    survivors (candidates whose `document_projection`
    was populated by the M8 adapter). Future milestones
    may swap this with a generation surface; the typedef
    is stable.
    """
    citations: list[dict[str, Any]] = []
    for ranked in retrieval_result.get("ranked") or ():
        candidate = ranked.get("candidate") or {}
        projection = candidate.get("document_projection")
        citations.append(
            {
                "chunk_id": candidate.get("chunk_id"),
                "document_id": candidate.get("document_id"),
                "ordinal": candidate.get("ordinal", 0),
                "quote": candidate.get("text_preview") or "",
                "department": (
                    (projection or {}).get("department") if projection else None
                ),
                "required_clearance": (
                    projection.get("required_clearance") if projection else None
                ),
            }
        )
    return citations


class RunQueryWorkflow:
    """M9 /v1/query orchestrator.

    The orchestrator wires:
      - The typed `WorkflowState` -> LangGraph channel.
      - The embedding + retrieval use cases + the M8
        orchestrator onto the LangGraph `retrieve`
        node.
      - The M9 `VerifyCitations` use case onto the
        `verify_citations` node.
      - The JSON envelope minting onto the
        `mint_response` node.

    The graph is sealed; the API layer calls
    `run_query(state)` and receives the JSON envelope.
    """

    def __init__(
        self,
        *,
        retrieval_orchestrator: RetrieveAuthorizedCandidates,
        citation_verifier: VerifyCitations,
        build_citations_fn: Optional[BuildCitationsFn] = None,
        rerank_top_n: int = 4,
        top_k: int = 8,
    ) -> None:
        self._retrieval_orchestrator = retrieval_orchestrator
        self._citation_verifier = citation_verifier
        self._build_citations = build_citations_fn or default_build_citations
        self._rerank_top_n = rerank_top_n
        self._top_k = top_k

    async def __call__(self, state: WorkflowState) -> dict[str, Any]:
        if not isinstance(state, WorkflowState):
            raise IncompleteActorError(
                "run_query requires a typed WorkflowState; "
                "construct via WorkflowState.from_actor(...) at the "
                "application boundary."
            )
        compiled = self._build_graph()
        initial = _initial_channel(state)
        final_channel = await compiled.ainvoke(initial)
        return _finalize(final_channel)


def _initial_channel(state: WorkflowState) -> _WorkflowChannel:
    return _WorkflowChannel(
        user_id=state.user_id,
        department=state.department,
        clearance=state.clearance,
        role=state.role,
        correlation_id=state.correlation_id,
        query=state.query,
    )


def _build_graph(self_holder) -> Any:
    """Compile the M9 graph.

    Captures the use cases on the orchestrator; the
    factory closure pattern avoids wiring cycles.
    """
    graph: StateGraph = StateGraph(state_schema=_WorkflowChannel)

    async def ingest_query(channel):
        return {"query": channel.get("query")}

    async def retrieve_authorized(channel):
        from src.application.auth.dto import AuthActor

        actor = AuthActor(
            user_id=channel.get("user_id", ""),
            department=channel.get("department", ""),
            clearance=channel.get("clearance", ""),
            role=channel.get("role", ""),
            correlation_id=channel.get("correlation_id", ""),
        )
        cmd = RetrieveAuthorizedCommand(
            actor=actor,
            query_text=channel.get("query") or "",
            top_k=self_holder._top_k,
            rerank_top_n=self_holder._rerank_top_n,
        )
        result = await self_holder._retrieval_orchestrator.execute(cmd)
        retrieval_result = _serialize_retrieval(result)
        citations = await self_holder._build_citations(
            # Build a temporary state-like view for citation
            # construction without mutating the workflow
            # state's query field semantics.
            _state_from_channel(channel),
            retrieval_result,
        )
        return {
            "authorization": retrieval_result["authorization"],
            "citations": citations,
        }

    async def verify_citations(channel):
        citations_dicts = channel.get("citations") or []
        from src.domain.ports.citations import Citation
        from src.domain.ports.clearances import Clearance
        from src.application.auth.dto import AuthActor

        citation_objs = []
        for c in citations_dicts:
            projection = c.get("required_clearance")
            if projection is not None:
                projection = Clearance(projection)
            from src.domain.ports.documents import DocumentProjection
            doc_projection = DocumentProjection(
                department=c.get("department"),
                required_clearance=projection if projection is not None else None,
            )
            citation_objs.append(
                Citation(
                    chunk_id=c["chunk_id"],
                    document_id=c["document_id"],
                    ordinal=c.get("ordinal", 0),
                    quote=c.get("quote", ""),
                    document_projection=doc_projection,
                )
            )
        actor = AuthActor(
            user_id=channel.get("user_id", ""),
            department=channel.get("department", ""),
            clearance=channel.get("clearance", ""),
            role=channel.get("role", ""),
            correlation_id=channel.get("correlation_id", ""),
        )
        result = await self_holder._citation_verifier.execute(
            VerifyCitationsCommand(actor=actor, citations=tuple(citation_objs))
        )
        allowed = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "ordinal": c.ordinal,
                "quote": c.quote,
            }
            for c in result.allowed_citations
        ]
        dropped = [
            {
                "chunk_id": drop.citation.chunk_id,
                "document_id": drop.citation.document_id,
                "ordinal": drop.citation.ordinal,
                "quote": drop.citation.quote,
                "reason": drop.reason,
            }
            for drop in result.dropped_citations
        ]
        return {
            "citations": allowed,
            "dropped_citations": dropped,
        }

    async def mint_response(channel):
        authorization = channel.get("authorization") or {}
        return {
            "authorization": authorization,
            "citations": channel.get("citations", []),
            "dropped_citations": channel.get("dropped_citations", []),
            "query": channel.get("query", ""),
            "correlation_id": channel.get("correlation_id", ""),
            "user_id": channel.get("user_id", ""),
            "department": channel.get("department", ""),
            "clearance": channel.get("clearance", ""),
        }

    graph.add_node("ingest_query", ingest_query)
    graph.add_node("retrieve_authorized", retrieve_authorized)
    graph.add_node("verify_citations", verify_citations)
    graph.add_node("mint_response", mint_response)
    graph.add_edge(START, "ingest_query")
    graph.add_edge("ingest_query", "retrieve_authorized")
    graph.add_edge("retrieve_authorized", "verify_citations")
    graph.add_edge("verify_citations", "mint_response")
    graph.add_edge("mint_response", END)
    return graph.compile()


def _state_from_channel(channel) -> WorkflowState:
    return WorkflowState(
        user_id=channel.get("user_id", ""),
        department=channel.get("department", ""),
        clearance=channel.get("clearance", ""),
        role=channel.get("role", ""),
        correlation_id=channel.get("correlation_id", ""),
        query=channel.get("query"),
    )


def _serialize_retrieval(result) -> dict[str, Any]:
    """Project the M8 typed result to a JSON-friendly dict.

    The M8 typed result carries frozen dataclasses; the
    JSON envelope needs plain dicts / ints / strs / lists.
    """
    authorization = result.authorization
    stats = result.stats
    ranked = []
    for r in result.ranked:
        cand = r.candidate
        ranked.append(
            {
                "candidate": {
                    "chunk_id": cand.chunk_id,
                    "document_id": cand.document_id,
                    "ordinal": cand.ordinal,
                    "dense_score": cand.dense_score,
                    "bm25_score": cand.bm25_score,
                    "text_preview": cand.text_preview,
                    "document_projection": (
                        {
                            "department": cand.document_projection.department,
                            "required_clearance": (
                                cand.document_projection.required_clearance.name
                                if cand.document_projection
                                and cand.document_projection.required_clearance
                                is not None
                                else None
                            ),
                        }
                        if cand.document_projection is not None
                        else None
                    ),
                },
                "score": r.score,
                "stage": r.stage,
            }
        )
    return {
        "authorization": {
            "allowed": authorization.allowed,
            "reason": authorization.reason,
            "policy_filter": {
                "allowed_departments": list(
                    authorization.policy_filter.allowed_departments
                ),
                "minimum_clearance": authorization.policy_filter.minimum_clearance,
                "decision_outcome": list(
                    authorization.policy_filter.decision_outcome
                ),
            },
        },
        "ranked": ranked,
        "stats": {
            "dense_count": stats.dense_count,
            "bm25_count": stats.bm25_count,
            "fused_count": stats.fused_count,
            "rerank_count": stats.rerank_count,
            "after_access_count": stats.after_access_count,
        },
    }


def _finalize(channel) -> dict[str, Any]:
    """Translate the LangGraph channel final-state to the JSON envelope."""
    return dict(channel)


# Bind the build_graph method to the orchestrator at module-load
# time. The Methodist is implemented above as a free function so
# the closure captures `self_holder` properly.
RunQueryWorkflow._build_graph = _build_graph  # type: ignore[attr-defined]


__all__ = ["RunQueryWorkflow", "_build_graph", "default_build_citations"]
