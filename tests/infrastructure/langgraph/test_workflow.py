"""M6 LangGraph adapter coverage.

Five distinct tests:

1. The compiled skeleton graph runs the empty state machine
   and a typed `WorkflowState` survives the round-trip.
2. `build_initial_channel` projects every required field
   from the typed state into the LangGraph channel shape.
3. `to_state_dict` returns a dict whose values exactly match
   the typed state (round-trip-shape preservation).
4. `run_workflow` is async and returns the typed state.
5. `from_state_dict` raises `IncompleteActorError` when a
   required field is omitted from the channel dict (defense
   in depth against framework-side surprises).
"""
from __future__ import annotations

import pytest

from src.application.auth.dto import AuthActor
from src.application.workflow.errors import IncompleteActorError
from src.application.workflow.state import WorkflowState
from src.infrastructure.langgraph.workflow import (
    build_initial_channel,
    build_skeleton_graph,
    from_state_dict,
    run_workflow,
    to_state_dict,
)


def _actor() -> AuthActor:
    return AuthActor(
        user_id="u-m6-graph",
        department="engineering",
        clearance="internal",
        role="contributor",
        correlation_id="corr-m6-graph",
    )


def _state_with_query() -> WorkflowState:
    return WorkflowState.from_actor(_actor(), query="hello workflow")


def test_build_initial_channel_includes_every_required_field():
    state = _state_with_query()
    ch = build_initial_channel(state)
    assert ch["user_id"] == "u-m6-graph"
    assert ch["department"] == "engineering"
    assert ch["clearance"] == "internal"
    assert ch["role"] == "contributor"
    assert ch["correlation_id"] == "corr-m6-graph"
    assert ch["query"] == "hello workflow"


def test_to_state_dict_round_trips_preserving_every_field():
    state = _state_with_query()
    ch = to_state_dict(state)
    rebuilt = WorkflowState(
        user_id=ch["user_id"],
        department=ch["department"],
        clearance=ch["clearance"],
        role=ch["role"],
        correlation_id=ch["correlation_id"],
        query=ch["query"],
    )
    assert rebuilt == state


def test_build_skeleton_graph_compiles_a_langgraph_state_graph():
    compiled = build_skeleton_graph()
    assert compiled is not None
    # CompiledStateGraph has `.invoke` and `.ainvoke`.
    assert hasattr(compiled, "invoke")
    assert hasattr(compiled, "ainvoke")


async def test_run_workflow_round_trips_through_empty_state_machine():
    state = _state_with_query()
    result = await run_workflow(state)
    assert result.user_id == state.user_id
    assert result.department == state.department
    assert result.clearance == state.clearance
    assert result.role == state.role
    assert result.correlation_id == state.correlation_id
    assert result.query == state.query


def test_from_state_dict_raises_when_required_field_missing():
    """Defense in depth: missing-required channel raises.

    The application factory `WorkflowState.from_actor(...)` is
    the canonical entry; this test bounds the framework-side
    reconstruction by exercising the same fail-closed behavior
    on the channel-dict projection.
    """
    with pytest.raises(IncompleteActorError):
        from_state_dict(
            {
                "user_id": "",
                "department": "engineering",
                "clearance": "internal",
                "role": "contributor",
                "correlation_id": "corr",
            }
        )
