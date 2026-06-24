"""M6 empty LangGraph state machine.

The skeleton graph proves the framework binding without
introducing any of the future-state-machine nodes (M7-M9).
The single `noop_node` returns the typed channel unchanged.

**Channel shape.** LangGraph 0.4 reads and writes a
`TypedDict`-shaped channel. The application package's typed
contract is a frozen dataclass (`WorkflowState`). The adapter:

  - `[to_state_dict(state)]` projects the frozen dataclass to
    the LangGraph channel shape.
  - `[from_state_dict(channel)]` rebuilds the frozen dataclass
    (returning the same instance if fields match) so the graph
    result is returned as the application-typed contract.

**State purity.** The adapter never mutates the typed input.
The compiled graph returns a new channel dict at the END edge;
the adapter reads it back into a fresh `WorkflowState` via the
typed factory (`from_actor` for partial channels is unavailable;
we use direct construction here **after** validating that no
required field became blank during graph traversal).

**`build_initial_channel`.** Helper that converts a typed
`WorkflowState` into the LangGraph-shaped channel for the
`StateGraph.invoke(...)` entry point.

**`build_skeleton_graph`.** Returns a freshly-compiled
`CompiledStateGraph` whose only node is `noop`. The compiled
graph can be invoked ad-hoc in tests.

**`run_workflow`.** The application entrypoint. Accepts a typed
`WorkflowState`, runs the empty skeleton, returns the typed
result.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.application.workflow.errors import IncompleteActorError
from src.application.workflow.state import WorkflowState


class _WorkflowChannel(TypedDict, total=False):
    """LangGraph channel shape.

    `total=False` makes every field optional **in the channel
    schema only**. The application-layer guarantee (no
    anonymous execution) is enforced before the channel is
    built: every field is populated when constructing
    `_WorkflowChannel` from a typed `WorkflowState`.
    """

    user_id: str
    department: str
    clearance: str
    role: str
    correlation_id: str
    query: str | None  # Optional[str] in the Python field type


def build_initial_channel(state: WorkflowState) -> _WorkflowChannel:
    """Project the application-typed state to a LangGraph channel."""
    return _WorkflowChannel(
        user_id=state.user_id,
        department=state.department,
        clearance=state.clearance,
        role=state.role,
        correlation_id=state.correlation_id,
        query=state.query,
    )


def from_state_dict(channel: dict[str, Any]) -> WorkflowState:
    """Rebuild a typed `WorkflowState` from a LangGraph channel dict.

    Raises `IncompleteActorError` if any required field is
    blank after graph traversal. This is the framework-side
    fail-closed companion to the application's typed factory;
    it ensures the typed contract is preserved end-to-end
    even when nodes misbehave.

    `asdict` would translate `Optional[str]` fields but our
    target type is the frozen dataclass itself so we rely on
    direct kwargs to preserve the same shape.
    """
    candidate = {
        "user_id": channel.get("user_id", ""),
        "department": channel.get("department", ""),
        "clearance": channel.get("clearance", ""),
        "role": channel.get("role", ""),
        "correlation_id": channel.get("correlation_id", ""),
        "query": channel.get("query"),
    }
    # Direct construction; `__post_init__` enforces non-blank
    # required fields. We deliberately avoid `from_actor` here
    # because the channel dict is not an AuthActor.
    return WorkflowState(
        user_id=candidate["user_id"],
        department=candidate["department"],
        clearance=candidate["clearance"],
        role=candidate["role"],
        correlation_id=candidate["correlation_id"],
        query=candidate["query"],
    )


def to_state_dict(state: WorkflowState) -> dict[str, Any]:
    """Compatibility variant of `build_initial_channel` returning a plain dict."""
    return dict(asdict(state))


def _noop_node(channel: _WorkflowChannel) -> dict[str, Any]:
    """The M6 empty state machine's only node.

    The node is identity: it returns the channel unchanged so
    the graph round-trips a typed state through the framework
    without mutation. Future milestones (M7+) replace this
    with the actual retrieval-and-rerank-and-generation nodes.
    """
    return dict(channel)


def build_skeleton_graph() -> Any:
    """Compile a minimal LangGraph state machine.

    Topologically:
        START -> `noop_node` -> END

    The compiled graph is framework-side; the application
    layer does not see it. Sites that need to invoke the
    workflow call `run_workflow(state)` instead.
    """
    graph: StateGraph = StateGraph(_WorkflowChannel)
    graph.add_node("noop_node", _noop_node)
    graph.add_edge(START, "noop_node")
    graph.add_edge("noop_node", END)
    return graph.compile()


async def run_workflow(state: WorkflowState) -> WorkflowState:
    """Application-side entry point.

    Accepts the typed M6 state, projects to the LangGraph
    channel, runs the empty skeleton, and reconstructs the
    typed result. The result preserves the `correlation_id`
    and `user_id` end-to-end so downstream consumers (M9+)
    can attribute every line of work to a verified actor.
    """
    if not isinstance(state, WorkflowState):
        raise IncompleteActorError(
            "run_workflow requires a typed WorkflowState; "
            "construct via WorkflowState.from_actor(...) at the "
            "application boundary."
        )
    compiled = build_skeleton_graph()
    initial = build_initial_channel(state)
    # LangGraph's compile() yields a sync invoke() and an
    # ainvoke(); the application entrypoint is async-aware so
    # we always call the async variant. The skeleton graph has
    # no I/O so it returns immediately.
    final_channel = await compiled.ainvoke(initial)
    return from_state_dict(final_channel)


__all__ = [
    "_WorkflowChannel",
    "build_initial_channel",
    "build_skeleton_graph",
    "from_state_dict",
    "run_workflow",
    "to_state_dict",
]
