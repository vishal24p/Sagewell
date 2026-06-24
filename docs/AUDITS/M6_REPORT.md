# M6 Closure — LangGraph Skeleton (actor-aware)

**Date**: 2026-06-21
**Milestone**: M6 — LangGraph Skeleton (actor-aware).
**Scope**: A runnable, empty LangGraph state machine bound to a typed application-layer `WorkflowState`; the workflow refuses to start when any of `user_id`, `department`, `clearance`, `role`, or `correlation_id` is missing. **No** retrieval, **no** reranking, **no** generation, **no** guards, **no** `/v1/*` routes. The M5 API surface (`/health`, `/openapi.json`, `/docs`, `/redoc` + JWT middleware) is unchanged.
**Status**: **CLOSED 2026-06-21** at this commit on `feat/m6-langgraph-skeleton`.
**Closure artifact**: this file plus the application / infrastructure / tests tree.

---

## Decision IDs Locked (this milestone)

| D-ID | Decision |
|---|---|
| D-045 | M6 ships `src/application/workflow/` as a third application-package sibling to `audit_event/` and `auth/`. The workflow package owns the typed `WorkflowState` dataclass and the typed-failure hierarchy (`WorkflowDomainError` -> `AnonymousExecutionError` -> `IncompleteActorError`). Imports only standard library and intra-application / domain. |
| D-046 | M6 introduces `src/infrastructure/langgraph/` as the framework-adapter layer. The adapter binds the typed application state to a LangGraph `StateGraph` channel shape via `build_initial_channel` (typed -> channel) and `from_state_dict` (channel -> typed). It is the only place in the project that imports `langgraph`. |
| D-047 | The application `WorkflowState` is a frozen dataclass with required fields `{user_id, department, clearance, role, correlation_id}` plus an optional `query`. Construction via the typed factory `WorkflowState.from_actor(actor)` is the canonical entry; direct `WorkflowState(...)` construction succeeds only when every required field is non-blank (frozen `__post_init__` invariant) — defense in depth. |
| D-048 | M6's `run_workflow(state)` is the canonical async application entrypoint. It rejects any non-`WorkflowState` input with `IncompleteActorError` and routes the typed state through `START -> noop_node -> END`. The skeleton node is identity: the channel returns unchanged. Future M7-M9 milestones replace `noop_node` with the V1 retrieval-and-rerank-and-generation graph. |
| D-049 | The workflow package **MUST NOT** import `src/api/`, `src/infrastructure/`, fastapi, pydantic, uvicorn, asyncpg, psycopg, sqlalchemy, or any framework SDK. This balances AGENTS.md's "domain code does not import LangGraph" rule by holding the framework adapter under `src/infrastructure/langgraph/` and letting the application package stay framework-free. Verified by an AST-based import-statement scan (run from the verification harness in M6). |
| D-050 | The M3/M5 API route surface is unchanged. The M3 launch contract (`uvicorn src.api.app:create_app --factory`) continues to boot without a database and without invoking the workflow. M6 deliberately does NOT wire any `/v1/*` route to `run_workflow`; the `/v1/*` endpoint lands at the milestone that wires the workflow to the JWT-derived actor (per the M6 description in `PROJECT_STATUS.md`). |
| D-051 | M6 widens the dependency surface: `langgraph>=0.4,<0.6` is added to `pyproject.toml`'s runtime dependencies. The version range matches the project's existing transferability pattern (avoid pinning a specific framework version). The driver-side LangGraph dependencies (`langchain-core`, `langgraph-checkpoint`, `langgraph-sdk`, `langgraph-prebuilt`) land transitively and remain capability-based — M6 does not commit to any future use of `langgraph-prebuilt` / `langgraph-checkpoint` (M9+ may introduce them). |

---

## Files Created Under M6

### Source

- `src/application/workflow/__init__.py` — application package surface.
- `src/application/workflow/state.py` — `WorkflowState` frozen dataclass with `from_actor` factory and `__post_init__` fail-closed invariant.
- `src/application/workflow/errors.py` — typed-error hierarchy (`WorkflowDomainError`, `AnonymousExecutionError`, `IncompleteActorError`).
- `src/infrastructure/langgraph/__init__.py` — framework-adapter surface.
- `src/infrastructure/langgraph/workflow.py` — `build_initial_channel`, `from_state_dict`, `to_state_dict`, `build_skeleton_graph`, `run_workflow`. The only file that imports `langgraph`.

### Tests

- `tests/application/workflow/test_workflow_state.py` — 8 distinct tests covering happy path, anonymous-execution block, blank-correlation-id block, direct-constructor block, blank-query block, frozen-immutability, query-projection, channel-key listing.
- `tests/infrastructure/langgraph/test_workflow.py` — 5 distinct tests covering initial-channel projection, `to_state_dict`, skeleton compilation, `run_workflow` round-trip, `from_state_dict` fail-closed.

### Documentation

- `docs/AUDITS/M6_REPORT.md` (this file).
- `docs/AUDITS/FINDINGS.md` — F-35 entry.
- `MEMORY.md` — M6 closure rows.
- `docs/AUDITS/AUDIT_HISTORY.md` — row 19.
- `docs/AUDITS/MILESTONE_GATES.md` — M6 row marked Closed.
- `docs/HANDOFF/CURRENT_STATE.md` — M6 row added to Completed, current branch updated.
- `docs/HANDOFF/DECISIONS_PENDING.md` — D-045..D-051 added.
- `NEXT_AGENT.md` — current milestone flips to M7 (Ingestion).
- `PROJECT_STATUS.md` — M6 description tightened; risks row updateds; M7 description refined.

---

## Files Modified Under M6

- `pyproject.toml` — adds `langgraph>=0.4,<0.6` to runtime dependencies.

(No other source files touched. M3/M4/M5 surfaces are unchanged.)

---

## Surface

### Public surface at the application boundary

```python
# src/application/workflow/__init__.py re-exports:
WorkflowState                       # frozen dataclass

# Errors re-exported at package boundary:
AnonymousExecutionError              # code = "anonymous_execution"
IncompleteActorError                 # code = "incomplete_actor"
   # subclass of AnonymousExecutionError
WorkflowDomainError                  # base, code = "workflow_failed"
```

### Typed factory

```python
actor = AuthActor(
    user_id="u-...",
    department="engineering",
    clearance="internal",
    role="contributor",
    correlation_id="corr-...",
)
state = WorkflowState.from_actor(actor, query="optional question")
# raises IncompleteActorError if any required field is blank.
```

### Infrastructure entrypoint

```python
# src/infrastructure/langgraph/__init__.py re-exports:
WorkflowState                       # re-exported from application
build_initial_channel(state)        # typed -> LangGraph channel
build_skeleton_graph()              # runnable StateGraph (only noop_node)
from_state_dict(channel)            # LangGraph channel -> typed
                                   # (raises IncompleteActorError)
to_state_dict(state)                # typed -> dict (no LangGraph call)
run_workflow(state)                 # async entry: returns typed state
```

### Boundary invariant (cross-layer)

- The application package imports ONLY stdlib + intra-application + domain ports.
- The infrastructure package imports `langgraph` + `src.application.workflow.*` + stdlib.
- The api package does NOT import `src/application/workflow/` or `src/infrastructure/langgraph/`. The D-028 forward-hook (workflow -> api, not api -> workflow) is preserved and is the canonical direction when M9 mounts a `/v1/*` route.

---

## Verification

```text
$ .venv\Scripts\python.exe -m pytest -q tests/application/workflow tests/infrastructure/langgraph
13 passed, 0 failed, 0 skipped

$ .venv\Scripts\python.exe -m pytest -q   # combined
86 passed, 52 skipped, 0 failed   # was 73 at M5; net +13 from M6
```

### Structural guards

- AST scan ("import-statement-level") of `src/application/**` and `src/domain/**`: zero `fastapi`, `pydantic`, `uvicorn`, `asyncpg`, `psycopg`, `sqlalchemy` import statements. Docstring-level "no asyncpg" decls are not import statements.
- AST scan confirms `langgraph` is imported only under `src/infrastructure/langgraph/workflow.py`.
- AST scan confirms `fastapi` / `pydantic` / `uvicorn` import statements live ONLY under `src/api/**` (allowed per architecture: api is the bulk layer).
- AST scan confirms `asyncpg` import statements live ONLY under `src/infrastructure/repositories/postgres/**` (allowed per architecture: infrastructure is the driver layer).

### Typed-state defensive checks

- `WorkflowState.from_actor(actor_with_empty_user_id)` raises `IncompleteActorError`.
- `WorkflowState(...)` with any blank required field raises `IncompleteActorError`.
- `state.with_query("   ")` raises `AnonymousExecutionError`.
- `run_workflow(not_a_workflow_state)` raises `IncompleteActorError`.
- `from_state_dict({"user_id": "", ...})` raises `IncompleteActorError`.

### LangGraph round-trip

- The skeleton graph returns the typed state with `user_id`, `department`, `clearance`, `role`, `correlation_id`, `query` unchanged.
- The async `ainvoke` call returns a channel dict with every key whose value matches the typed state's fields.

---

## Architectural drift discovered (none new)

- The LangGraph adapter splits into two layers: `_WorkflowChannel` (TypedDict with `total=False` per langgraph idioms) and the typed `WorkflowState` (frozen dataclass). The `total=False` flag is the langgraph-side channel-shape contract; typing-side, the application dataclass refuses non-blank required fields. The two layers never collapse: the channel shape is mutable / schema for the framework; the state is immutable / contract for the application code.
- The `from_actor` factory accepts an M5 `AuthActor` (sibling application import). This is the canonical entry although the typed dataclass could be built directly from a verified-actor dict. Direct constructor calls bypass any pre-validation, which `__post_init__` and the framework adapter's `from_state_dict` then enforce fill-closed. Future M7+ milestones that introduce richer actors (with department/clearance lowered against the access-decision hierarchy) can subclass or compose `AuthActor` without disturbing the factory signature.
- No `/v1/*` route mounts `run_workflow` at M6. The M3/M5 route surface (`/health`, `/openapi.json`, `/docs`, `/redoc`) continues to be the API boundary. Adding a `/v1/*` endpoint that invokes `run_workflow(state)` lands at the milestone that wires the V1 retrieval / guards / generation pipeline, not at M6.

---

## Findings raised during M6

| ID | Tag | Title | Status |
|---|---|---|---|
| F-35 | LOW | The langgraph `TypedDict` for the channel uses `total=False` so langgraph's state-diff machinery can read partial / intermediate channels during graph traversal. This is the langgraph-side schema — the application-side `WorkflowState` is the typed contract that forbids partial / anonymous state. The two layers are intentionally not collapsed: the channel is mutable / framework-side, the dataclass is immutable / contract-side. | Accepted-Low. Documented in this report. |

---

## Out of scope (deferred)

- No retrieval stages (dense / BM25 / RRF / cross-encoder); M8.
- No regex guard / LLM guard; M10 / M11.
- No `/v1/*` route; lands at M9 (workflow wiring).
- No audit-log or retrieval-log writes through M4's use case; M12.
- No RBAC-filter SQL push-down or post-rerank drop; M8.
- No citation verification; M9.
- No model SDK dependencies for embedding / generation / guard / reranker. The framework layer (LangGraph) is wired at M6 but every node beyond `noop` remains a future-milestone concern.
- No return to the M5 `/v1/*` path. The D-028 forward hook rule (`workflow -> api` direction only) is preserved; M6 introduces no reversal.

---

## Next milestone

M7 — Ingestion. The future consumer of M6's `WorkflowState` and LangGraph skeleton is the M7 ingestion node: it will populate workflow-side metadata from the connector / LlamaIndex adapter pair. Until M7 lands, `noop_node` is identity; the workflow can be invoked with a typed `AuthActor` and (optionally) a `query`, and it returns the typed state unchanged.
