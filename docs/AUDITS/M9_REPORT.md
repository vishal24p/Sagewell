# M9 Closure — Workflow Wiring with Citations

**Date**: 2026-06-26
**Milestone**: M9 — Workflow Wiring with Citations.
**Scope**: The M8 retrieval orchestrator is bound onto the M6 LangGraph skeleton as a typed node in the state machine. The citation-verification step (the third invocation of the M0 pure function per `AGENTS.md` Architectural Guardrails) lands at this milestone. The `/v1/query` route ships on the API surface bound to the typed orchestrator. **No** generation, regex-guard, or LLM-guard at M9 — these are M11+ and M12+.
**Status**: **CLOSED 2026-06-26** on `feat/m9-workflow-citations`.
**Closure artifact**: this file plus the application / infrastructure / tests tree.
**Pytest baseline**: 130 passed (was 118 at M8 closure; net +12 from M9), 52 skipped, 0 failed.

---

## Decision IDs Locked (this milestone)

| D-ID | Decision |
|---|---|
| D-072 | M9 introduces `src/domain/ports/citations.py` carrying the `Citation` typed contract (`chunk_id`, `document_id`, `ordinal`, `quote`, optional `document_projection`). The verifier passes the `document_projection` through to the pure function so it short-circuits when the adapter pre-populated it. |
| D-073 | M9 introduces `src/application/citations/verify.py::VerifyCitations` orchestrator. The use case is async; accepts `VerifyCitationsCommand` carrying the typed `AuthActor` and a `Sequence[Citation]`; returns `VerifyCitationsResult` with `(allowed_citations, dropped_citations, total)`. The verifier invokes `decide(user, document)` once per citation -- never re-implements the access rule. |
| D-074 | The verifier is fail-closed on missing inputs. `documents_by_id` returning `None` cascades through the M0 pure function as `missing_document_department` / `missing_document_clearance`. The actor's blank clearance short-circuits to `missing_user_clearance` for every citation. Unrecognized non-blank clearances raise `CitationDecisionUnavailableError` so the workflow boundary can translate the failure. |
| D-075 | The verifier raised `EmptyCitationsError` when invoked with zero citations. The error carries `code: empty_citations`; this is a 400-class input validation failure, not a 503. |
| D-076 | M9 introduces `src/infrastructure/langgraph/run_query.py::RunQueryWorkflow`. The orchestrator wires `RetrieveAuthorizedCandidates` (M8) and `VerifyCitations` (M9) onto a typed LangGraph state machine: `ingest_query -> retrieve_authorized -> verify_citations -> mint_response`. The capability adapters (embedder, dense, BM25, reranker, retrieval orchestrator, citation verifier) are constructor-injected for testability. |
| D-077 | M9 ships `/v1/query` on the API surface (`src/api/routers/query.py`). The route reads the typed `AuthActor` placed by the M5 JWT middleware, builds `WorkflowState.from_actor(actor, query=...)`, calls a `run_query` callable bound through `create_app(..., run_query=...)` (typed via `RunQueryFn` Protocol in `src/api/protocols.py`). The route returns typed JSON; missing actor -> 401; blank query -> 400; missing `run_query` -> 503. |
| D-078 | The launch contract changes shape at M9. With `create_app()` alone (no DI) the API still boots but `/v1/query` returns 503 because no `run_query` callable is wired. With `create_app(run_query=...)` the `/v1/query` route returns 200 and a JSON envelope. The DB-free launch contract is preserved because the `run_query` callable can be a stub in production tests. |
| D-079 | M9 widens the API route surface test: the M3 strict guard at `tests/api/test_openapi.py` is replaced with the M9 guard that allows `/health` and `/v1/query`. The launch shape is updated accordingly. |
| D-080 | M9 preserves the D-028 forward hook: `src/api/routers/query.py` imports the workflow package; the workflow package imports nothing from `src/api/`. Verified by AST scan. |

---

## Files Created Under M9

### Source

- `src/domain/ports/citations.py` — `Citation` typed contract.
- `src/application/citations/__init__.py` — package surface.
- `src/application/citations/verify.py` — `VerifyCitations` orchestrator + `VerifyCitationsCommand`, `VerifyCitationsResult`, `DroppedCitation`, typed-error hierarchy.
- `src/api/protocols.py` — `RunQueryFn` Protocol.
- `src/api/routers/query.py` — `/v1/query` route handler.
- `src/infrastructure/langgraph/run_query.py` — `RunQueryWorkflow` LangGraph state machine.

### Tests

- `tests/application/citations/test_verify_citations.py` — six tests: happy path drops unauthorized; fail-closed on missing document; missing-user-clearance short circuits; pre-projected document skips lookup; empty citations raises typed error; unrecognized clearance raises decision-unavailable.
- `tests/api/test_v1_query_route.py` — four tests: missing actor returns 401; success returns envelope; blank query returns 400; missing run_query returns 503.
- `tests/infrastructure/langgraph/test_run_query_workflow.py` — two tests: empty pipeline raises the typed error; happy-path-end-to-end drops unauthorized citation.
- `tests/api/test_openapi.py` — route surface guard updated for M9 (`/health`, `/v1/query` only).

### Documentation

- `docs/AUDITS/M9_REPORT.md` (this file).
- `docs/AUDITS/MILESTONE_GATES.md` — M9 row marked Closed.
- `docs/AUDITS/AUDIT_HISTORY.md` — row 22 added.
- `docs/AUDITS/FINDINGS.md` — F-41 added.
- `docs/HANDOFF/CURRENT_STATE.md` — M9 added to Completed.
- `docs/HANDOFF/DECISIONS_PENDING.md` — D-072..D-080 added to Approved.
- `MEMORY.md` — M9 closure row + D-072..D-080.
- `NEXT_AGENT.md` — Current Milestone flipped to M10 (Regex Guard).
- `PROJECT_STATUS.md` — State line update.

---

## Files Modified Under M9

- `src/api/app.py` — `create_app(...)` accepts `run_query: Optional[RunQueryFn]`; mounts `/v1/query` router.
- `src/domain/ports/__init__.py` — docstring update for `citations.py`.
- `tests/api/test_openapi.py` — route-surface guard widens to M9 (`/health`, `/v1/query`).

(No M0..M8 surfaces were modified. The application boundary at M4 (`RecordAuditEvent`), M5 (`VerifyJwtToken`), M6 (`WorkflowState`), M7 (`IngestDocument`), and M8 (`RetrieveAuthorizedCandidates`) are preserved.)

---

## Surface

### Public application boundary

```python
# src/application/citations/__init__.py re-exports:
VerifyCitations                       # use case (async)
VerifyCitationsCommand                # typed command dataclass
VerifyCitationsResult                 # typed result dataclass
DroppedCitation                       # typed drop carrier
CitationVerificationError             # base; code = "citation_verification_failure"
EmptyCitationsError                   # code = "empty_citations"
CitationDecisionUnavailableError      # code = "citation_decision_unavailable"
```

### Domain ports (framework-free)

```python
# src/domain/ports/citations.py
@dataclass(frozen=True)
class Citation:
    chunk_id: int
    document_id: int
    ordinal: int
    quote: str
    document_projection: Optional[DocumentProjection] = None
```

### Infrastructure adapters

```python
# src/infrastructure/langgraph/run_query.py
class RunQueryWorkflow:
    def __init__(
        self,
        *,
        retrieval_orchestrator: RetrieveAuthorizedCandidates,
        citation_verifier: VerifyCitations,
        build_citations_fn: Optional[BuildCitationsFn] = None,
        rerank_top_n: int = 4,
        top_k: int = 8,
    ) -> None: ...

    async def __call__(self, state: WorkflowState) -> dict[str, Any]: ...
```

### API surface

```text
POST /v1/query
  body: {"query": "<non-blank>"}
  response 200: {"query", "user_id", "department", "clearance",
                 "correlation_id", "authorization", "citations",
                 "dropped_citations"}
  response 400: validation_error envelope
                (missing or blank query)
  response 401: unauthorized envelope (missing actor)
  response 503: service_unavailable envelope
                (run_query callable not wired)
```

### Pipeline contract

```text
START -> ingest_query    (carries the typed query through)
       -> retrieve_authorized   (M8 orchestrator)
       -> verify_citations      (M9 orchestrator; M0 third invocation)
       -> mint_response         (canonical JSON envelope)
       -> END
```

---

## Verification

```text
.venv\Scripts\python.exe -m pytest -q tests/application/citations
6 passed, 0 failed, 0 skipped

.venv\Scripts\python.exe -m pytest -q tests/api/test_v1_query_route.py
4 passed, 0 failed, 0 skipped

.venv\Scripts\python.exe -m pytest -q tests/infrastructure/langgraph/test_run_query_workflow.py
2 passed, 0 failed, 0 skipped

.venv\Scripts\python.exe -m pytest -q   # combined
130 passed, 52 skipped, 0 failed   # was 118 at M8 closure; net +12 from M9
```

### Structural guards

- AST scan of `src/application/citations/`: zero `fastapi`/`pydantic`/`uvicorn`/`asyncpg`/`psycopg`/`sqlalchemy`/`langgraph`/`llama_index` import statements.
- AST scan of `src/api/routers/query.py`: imports the typed workflow package; the workflow package does NOT import anything under `src/api/`.
- AST scan of `src/infrastructure/langgraph/run_query.py`: zero `fastapi`/`pydantic`/`asyncpg`/`psycopg`/`sqlalchemy` imports; `langgraph` is imported from the M9 adapter only.
- The OpenAPI surface test pins the M9 route surface (`/health`, `/v1/query` only).

### Typed-state defensive checks

- `VerifyCitations.execute` on empty input raises `EmptyCitationsError`.
- `VerifyCitations.execute` on blank actor clearance cascades to `missing_user_clearance` for every citation.
- `VerifyCitations.execute` on a citation whose `documents_by_id` returns `None` cascades to `missing_document_department` / `missing_document_clearance`.
- `VerifyCitations.execute` on unrecognized non-blank clearance raises `CitationDecisionUnavailableError`.
- `/v1/query` on missing actor returns 401 with the canonical envelope.
- `/v1/query` on blank query returns 400 with `code=validation_error`.
- `/v1/query` on missing `run_query` callable returns 503 with `code=service_unavailable`.

### Access-decision integration guarantees

- The M9 verifier calls the M0 pure function exactly once per citation. Caching is NOT introduced.
- The M9 verifier NEVER re-implements the access rule; it forwards the typed actor projection + document projection to `decide()`.
- The M9 verifier returns `(allowed_citations, dropped_citations, total)` without audit-row writes. Audit-on-drop is left to M12 (audit-and-retrieval-logs complete).

---

## Architectural decisions (review)

- The access-decision pure function is now invoked at three boundaries per `AGENTS.md` Architectural Guardrails: (1) pre-retrieval projection (M8), (2) post-rerank drop (M8), (3) citation verification (M9). No additional M0 invocation lands until M11 / M12.
- The application-boundary discipline (`repositories -> application -> domain`) is preserved; the framework adapter under `src/infrastructure/langgraph/run_query.py` is the only place that imports `langgraph`.
- The launch contract changes shape at M9. With `create_app()` (no DI), the API still boots and `/health` works, but `/v1/query` returns 503. With `create_app(run_query=...)`, the route returns 200 and a JSON envelope. The DB-free launch contract is preserved: the `run_query` callable can be a stub.
- The route layer imports the workflow package only. The workflow package does NOT import anything under `src/api/`. D-028 forward-hook preserved.

---

## Findings raised during M9

| ID | Tag | Title | Status |
|---|---|---|---|
| F-41 | LOW | The M9 `/v1/query` route runs only when `run_query` is wired through `create_app(...)`. When the runtime is launched without DI the route returns 503, but `/health` continues to return 200; the launch contract stays DB-free. Production wiring requires the M9 orchestrator to be passed. | Accepted-Low. Documented in this report. |

---

## Out of scope (deferred)

- No generation. The M9 orchestrator returns the post-citation-verification envelope; the generation model capability (D-005) lands at its own milestone.
- No Regex Guard. M10 introduces pattern-based refusals on the primary request path.
- No LLM Guard. M11 introduces the Guardrail Model (D-004) onto the M9 pipeline.
- No `audit_logs` write from the verifier. M12 introduces the audit-and-retrieval-logs surface; the verifier integrates there.
- No RAGAS evaluation. M13.
- No end-to-end hardening. M14.
- No model SDK pinning. Embedding Model, Reranker Model, Generation Model, Guardrail Model capabilities remain deferred per D-002..D-005.

---

## Next milestone

M10 — Regex Guard. Pattern-based refusals are introduced on the primary request path per `POLICIES.md`. The `/v1/query` route gains an upstream `RegexGuard` node that runs BEFORE the M9 retrieval + citation-verification pipeline. The M0 access-decision function is untouched; the regex guard is a separate compile-time + runtime pattern matcher that returns `regex_refused` reason codes.
