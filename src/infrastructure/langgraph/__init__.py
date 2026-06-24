"""M6 `src/infrastructure/langgraph/` adapter surface.

This package binds the framework lifecycle (LangGraph
`StateGraph`, `CompiledStateGraph`, channels, nodes) to the
application's typed `WorkflowState`. The infrastructure layer
is the only layer that imports LangGraph.

Boundary contract:

  - `src/infrastructure/langgraph/` imports `src.application.workflow`
    (intra-application). It does NOT import the api, auth, or
    audit_event packages directly.

  - The application package does NOT import anything under
    `src/infrastructure/`. The dependency direction is
    `infrastructure -> application -> domain` per ARCHITECTURE.md.

  - The LangGraph workflow definition is an implementation
    detail. The application entrypoint (M9 wiring) receives
    a `WorkflowState` and runs the compiled graph through the
    `run_workflow` callable below. The compiled graph is
    framework-side and never leaks into the api or
    application layers.

M6 ships the empty state machine: `START -> noop_node ->
END`. The empty node proves the framework binding without
introducing retrieval, generation, or guards from M7+.

Future milestones:

  - M7 wires the connector/discovery node into the state
    machine; only when the workflow state has a populated
    `query` field.
  - M8 wires Dense/BM25 retrieval and RRF + cross-encoder.
  - M9 wires the access-decision boundaries (constraint and
    drop-after-rerank).
  - M10/M11 wire the regex guard and LLM guard.
  - M12 wires audit and retrieval log persistence.
"""
from src.application.workflow.state import WorkflowState
from src.infrastructure.langgraph.workflow import (
    build_initial_channel,
    build_skeleton_graph,
    run_workflow,
)


__all__ = [
    "WorkflowState",
    "build_initial_channel",
    "build_skeleton_graph",
    "run_workflow",
]
