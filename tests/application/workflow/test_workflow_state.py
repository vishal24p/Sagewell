"""M6 `WorkflowState` typed-state coverage.

Five distinct tests:

1. `from_actor` happy path: a well-formed M5 `AuthActor` produces
   a fully typed state.
2. Empty `user_id` raises `IncompleteActorError` (anonymous
   execution forbidden).
3. Direct `WorkflowState(...)` construction with a blank
   required field triggers the `__post_init__` fail-closed — a
   defense-in-depth companion to `from_actor` in case a
   framework adapter misuses the constructor.
4. `with_query` rejects blank queries.
5. `from_actor` carries the `correlation_id` through verbatim
   even when the caller holds it only on the `AuthActor`
   (not via middleware).
"""
from __future__ import annotations

import pytest

from src.application.auth.dto import AuthActor
from src.application.workflow.errors import (
    AnonymousExecutionError,
    IncompleteActorError,
)
from src.application.workflow.state import WorkflowState


def _actor(**overrides) -> AuthActor:
    """Build a typed AuthActor; override any field via kwargs."""
    base = dict(
        user_id="u-m6",
        department="engineering",
        clearance="internal",
        role="contributor",
        correlation_id="corr-m6-test",
    )
    base.update(overrides)
    return AuthActor(**base)


def test_from_actor_happy_path_returns_typed_state():
    actor = _actor()
    state = WorkflowState.from_actor(actor)
    assert state.user_id == "u-m6"
    assert state.department == "engineering"
    assert state.clearance == "internal"
    assert state.role == "contributor"
    assert state.correlation_id == "corr-m6-test"
    assert state.query is None
    assert state.required_field_names() == (
        "user_id",
        "department",
        "clearance",
        "role",
        "correlation_id",
    )


def test_from_actor_with_blank_user_id_raises_incomplete_actor():
    actor = _actor(user_id="")
    with pytest.raises(IncompleteActorError):
        WorkflowState.from_actor(actor)


def test_from_actor_with_blank_correlation_id_raises():
    actor = _actor(correlation_id="   ")
    with pytest.raises(IncompleteActorError):
        WorkflowState.from_actor(actor)


def test_direct_constructor_blocks_anonymous_state_in_post_init():
    """Defense-in-depth: even direct `WorkflowState(...)` is fail-closed."""
    with pytest.raises(IncompleteActorError):
        WorkflowState(
            user_id="",  # anonymous string only
            department="engineering",
            clearance="internal",
            role="contributor",
            correlation_id="corr",
        )


def test_with_query_rejects_blank_query():
    actor = _actor()
    state = WorkflowState.from_actor(actor)
    with pytest.raises(AnonymousExecutionError):
        state.with_query("   ")


def test_from_actor_carries_query_through_when_provided():
    actor = _actor()
    state = WorkflowState.from_actor(actor, query="what is M6?")
    assert state.query == "what is M6?"


def test_state_is_frozen_dataclass_immutable():
    actor = _actor()
    state = WorkflowState.from_actor(actor)
    with pytest.raises(Exception):
        # Frozen dataclass blocks setattr.
        state.user_id = "u-impersonator"  # type: ignore[misc]


def test_channel_keys_lists_required_and_optional_fields():
    actor = _actor()
    state = WorkflowState.from_actor(actor)
    keys = state.channel_keys()
    assert "user_id" in keys
    assert "department" in keys
    assert "clearance" in keys
    assert "role" in keys
    assert "correlation_id" in keys
    assert "query" in keys  # optional but present in the channel
