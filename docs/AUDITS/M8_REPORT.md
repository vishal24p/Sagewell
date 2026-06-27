# M8 Closure — Retrieval with Access Filter

**Date**: 2026-06-26
**Milestone**: M8 — Retrieval with Access Filter.
**Scope**: The four mandatory retrieval stages (Dense, BM25, RRF fusion, Cross-Encoder reranking) per `skills/project/retrieval_engine/SKILL.md`. The M8 surface ships framework-free protocols at `src/domain/ports/retrieval.py`, a pure RRF implementation at `src/domain/retrieval/rrf.py`, the application-side orchestrator at `src/application/retrieval/retrieve.py` that wires pre-filter projection + post-rerank drop around the four stages, in-memory infrastructure adapters at `src/infrastructure/retrieval/` (Dense, BM25, Identity Reranker), and full test coverage. **No** new `/v1/...` endpoint at M8 — the orchestrator is exercised through tests. M9 wires the orchestrator onto the API surface.
**Status**: **CLOSED 2026-06-26** on `feat/m8-retrieval`.
**Closure artifact**: this file plus the application / domain / infrastructure / tests tree.
**Pytest baseline**: 118 passed, 52 skipped, 0 failed (was 103 at M7 closure; net +15 from M8).

---

## Decision IDs Locked (this milestone)

| D-ID | Decision |
|---|---|
| D-061 | M8 introduces four framework-free retrieval protocols under `src/domain/ports/retrieval.py`: `DenseRetrieverProtocol.retrieve(query, embedding) -> Sequence[RetrievalCandidate]`, `Bm25RetrieverProtocol.retrieve(query) -> Sequence[RetrievalCandidate]`, `RerankerProtocol.rerank(query, candidates, top_n) -> Sequence[RankedCandidate]`, and a re-export of M7's `QueryEmbedderProtocol`. The protocols are async; framework adapters may wrap a synchronous pgvector / pg_search call behind `await`. The application package imports the protocols only — never the framework adapters. |
| D-062 | M8 introduces `AccessPolicyFilter` as the typed projection of the M0 access-decision onto the SQL filter level. `AccessPolicyFilter` carries `allowed_departments: tuple[str, ...]`, `minimum_clearance: str` (the V1 canonical uppercase ladder step), and `decision_outcome: tuple[bool, str]` (the literal `(allowed, reason)` pair from `decide()`). The dense / BM25 adapters translate the projection into a SQL `WHERE` clause (or an in-memory filter predicate); the access decision is NEVER re-implemented at the adapter layer. |
| D-063 | M8 introduces `RetrievalCandidate` carrying `document_projection: Optional[DocumentProjection]`. The post-rerank drop reads this field; when it is `None`, the drop is deferred to the M9 citation-verification step. The in-memory and Postgres adapters populate the projection so the orchestrator short-circuits without a `documents_by_chunk_id` round-trip. |
| D-064 | `RetrieveAuthorizedCandidates` (`src/application/retrieval/retrieve.py`) wires seven stages: pre-filter projection (M0 pure function) -> embed (M7 capability) -> dense retrieval (M8 adapter) -> BM25 retrieval (M8 adapter) -> RRF fusion (pure function) -> cross-encoder rerank (M8 adapter, optional) -> post-rerank drop (M0 pure function). The flow is fixed; future optimizations (e.g., async fan-out of dense + BM25) land at the framework-adapter layer, not in the orchestrator. |
| D-065 | `_clearance_from_str()` is the JWT-supplied clearance string translator. It is case-insensitive (the JWT emits lowercase; the V1 enum is uppercase). `None` is returned when the string is blank — the M0 pure function's fail-closed rule then issues `missing_user_clearance`. Empty-string or otherwise unrecognized clearances raise `AccessDecisionUnavailableError` so the workflow boundary at M9 can translate. |
| D-066 | `EmptyRetrievalError` (`src/application/retrieval/errors.py`) is raised when both dense AND BM25 return zero candidates. This is the M8 closure rule: a zero-row retrieval set is a 503-class failure, not a success. The error carries the correlation_id for the M12 retrieval_logs row. |
| D-067 | `_safe_audit_failure_isolation_style` rules still apply at M8 boundary: the orchestrator does not write audit rows directly; M9 wires the audit-write step onto the workflow state. The orchestrator never raises for a SQL-filter mismatch — it returns the typed `AuthorizationOutcome(allowed=False, reason=...)` with `ranked=tuple()` and `stats.zeros()`. |
| D-068 | The in-memory dense / BM25 adapters (`src/infrastructure/retrieval/in_memory_dense.py`, `in_memory_bm25.py`) implement the canonical M8 algorithms: cosine-similarity scan over the in-memory catalog for Dense; BM25 with `k1=1.5`, `b=0.75` (ParadeDB / pg_search defaults) for BM25. Both adapters honor the `AccessPolicyFilter` projection the same way the SQL adapters will, so the dense / BM25 candidate sets stay aligned. |
| D-069 | `IdentityReranker` (`src/infrastructure/retrieval/identity_reranker.py`) is the V1 cross-encoder stub. It sorts by descending score and applies the `top_n` cap; the cross-encoder capability is the hosted-reranker adoption question D-003, which lives in a future milestone. The application surface does not change when the hosted reranker replaces this stub. |
| D-070 | M8 introduces zero `/v1/...` endpoints. The orchestrator's execute path is async-only; the `/health`, `/openapi.json`, `/docs`, `/redoc` routes from M3/M6 remain unchanged. M9 wires the orchestrator onto the M9 route surface. |
| D-071 | `src/domain/retrieval/rrf.py::fuse(dense_ranked, bm25_ranked, *, k=60)` is a pure function. Negative `k` raises `ValueError`. Tie-breaking is deterministic by `(document_id ASC, chunk_id ASC)`. The function emits `RankedItem` and `FusedCandidate` dataclasses; no I/O boundary, no framework import. |

---

## Files Created Under M8

### Source

- `src/domain/ports/retrieval.py` — `AccessPolicyFilter`, `RetrievalQuery`, `RetrievalCandidate`, `RankedCandidate`, `RetrievalStageStats`, `DenseRetrieverProtocol`, `Bm25RetrieverProtocol`, `RerankerProtocol`, `QueryEmbedderProtocol` re-export.
- `src/domain/retrieval/__init__.py` — package surface (re-exports).
- `src/domain/retrieval/rrf.py` — `fuse`, `RankedItem`, `FusedCandidate`, `DEFAULT_RRF_K=60`.
- `src/application/retrieval/__init__.py` — package surface (re-exports).
- `src/application/retrieval/errors.py` — typed-error hierarchy: `RetrievalDomainError` -> `EmptyRetrievalError`, `AccessDecisionUnavailableError`.
- `src/application/retrieval/retrieve.py` — `RetrieveAuthorizedCandidates` orchestrator + `RetrieveAuthorizedCommand`, `RetrieveAuthorizedResult`, `AuthorizationOutcome`.
- `src/infrastructure/retrieval/__init__.py` — package surface.
- `src/infrastructure/retrieval/in_memory_dense.py` — `InMemoryDenseRetriever`, `InMemoryDenseRow`, `InMemoryDenseStore`.
- `src/infrastructure/retrieval/in_memory_bm25.py` — `InMemoryBm25Retriever`, `InMemoryBm25Document`, `InMemoryBm25Store` (BM25 with `k1=1.5`, `b=0.75`).
- `src/infrastructure/retrieval/identity_reranker.py` — `IdentityReranker`.

### Tests

- `tests/domain/retrieval/test_rrf.py` — six RRF tests: disjoint, overlap-sum, sort-order, tie-break, negative-K rejection, custom-K.
- `tests/application/retrieval/conftest.py` — `StaticEmbedder`, `StaticDenseRetriever`, `StaticBm25Retriever`, `StaticReranker`, `_FakeDocs`, fixtures (`actor`, `make_cmd`, `use_case_factory`, `fake_docs`, `lookup`).
- `tests/application/retrieval/test_retrieve_authorized_candidates.py` — six tests: happy path (dense + BM25 + rerank + drop end-to-end), authorization outcome carries policy filter, deny-at-projection returns empty, raises on empty retrieval, rejects malformed embedding, rerank-skip when reranker is None.
- `tests/infrastructure/retrieval/test_in_memory_retrievers.py` — three tests: dense applies access filter, BM25 respects filter and tokenizes, identity reranker caps top_n and preserves `document_projection`.

### Documentation

- `docs/AUDITS/M8_REPORT.md` (this file).
- `docs/AUDITS/MILESTONE_GATES.md` — M8 row marked Closed.
- `docs/AUDITS/AUDIT_HISTORY.md` — row 21.
- `docs/AUDITS/FINDINGS.md` — F-39, F-40 (Low-severity hygiene).
- `docs/HANDOFF/CURRENT_STATE.md` — M8 row added to Completed.
- `docs/HANDOFF/DECISIONS_PENDING.md` — D-061..D-071 added to Approved.
- `MEMORY.md` — closure row + decisions D-061..D-071.
- `NEXT_AGENT.md` — flips Current Milestone to M9 (Workflow Wiring with Citations).
- `PROJECT_STATUS.md` — State line update.

---

## Files Modified Under M8

- `AGENTS.md` — `When Unsure` section gains the `goal` + `autoplan` pointer.
- `SKILLS.md` — `Vendored External Skills` table adds `skills/external/goal/SKILL.md` (the `gstack-define-goal` route).
- `skills/external/goal/SKILL.md` — vendored at this commit (the skill file content was already present from a prior session).
- `tests/application/ingestion/test_ingest_document.py` — companion fix kept the M7 SKIPPED-as-ALLOWED regression test live (docstring now reads "Eight distinct tests").

(No M0..M7 surface files were modified by M8. The application boundary at M4 (`RecordAuditEvent`), M5 (`AuthenticatedActor`), and M7 (`IngestDocument`) are preserved.)

---

## Surface

### Public application boundary

```python
# src/application/retrieval/__init__.py re-exports:
RetrieveAuthorizedCandidates          # use case (async)
RetrieveAuthorizedCommand             # typed command dataclass
RetrieveAuthorizedResult              # typed result dataclass
AuthorizationOutcome                  # typed dataclass: allowed, reason, policy_filter
EmptyRetrievalError                   # code = "empty_retrieval"
AccessDecisionUnavailableError        # code = "access_decision_unavailable"
RetrievalDomainError                  # base; code = "retrieval_domain_error"
```

### Domain ports (framework-free)

```python
# src/domain/ports/retrieval.py
class DenseRetrieverProtocol(Protocol):
    async def retrieve(
        self,
        query: RetrievalQuery,
        embedding: list[float],
    ) -> Sequence[RetrievalCandidate]: ...

class Bm25RetrieverProtocol(Protocol):
    async def retrieve(self, query) -> Sequence[RetrievalCandidate]: ...

class RerankerProtocol(Protocol):
    async def rerank(
        self,
        query: RetrievalQuery,
        candidates: Sequence[RankedCandidate],
        top_n: int,
    ) -> Sequence[RankedCandidate]: ...


@dataclass(frozen=True)
class AccessPolicyFilter:
    allowed_departments: tuple[str, ...]
    minimum_clearance: str
    decision_outcome: tuple[bool, str]


@dataclass(frozen=True)
class RetrievalStageStats:
    dense_count: int
    bm25_count: int
    fused_count: int
    rerank_count: int
    after_access_count: int


# src/domain/retrieval/rrf.py
@dataclass(frozen=True)
class RankedItem:
    chunk_id: int
    document_id: int
    score: float


@dataclass(frozen=True)
class FusedCandidate:
    chunk_id: int
    document_id: int
    dense_score: Optional[float]
    bm25_score: Optional[float]
    fused_score: float
    dense_rank: Optional[int]
    bm25_rank: Optional[int]


def fuse(
    dense_ranked: Sequence[RankedItem],
    bm25_ranked: Sequence[RankedItem],
    *,
    k: int = 60,
) -> list[FusedCandidate]: ...
```

### Infrastructure adapters

```python
# src/infrastructure/retrieval/__init__.py re-exports:
InMemoryDenseRetriever                # cosine-similarity scan, in-memory
InMemoryDenseRow                      # canonical row schema
InMemoryDenseStore                    # list-store aggregator
InMemoryBm25Retriever                 # BM25 k1=1.5, b=0.75 over text fields
InMemoryBm25Document                  # canonical text row schema
InMemoryBm25Store                     # list-store aggregator
IdentityReranker                      # sort+top_n stub; replaced at hosted-reranker adoption milestone D-003
```

### Pipeline contract

```text
PRE-FILTER PROJECTION (M0):
  user = UserProjection(department, clearance_enum)
  doc = DocumentProjection(department="ALL", required_clearance=clearance_enum)
  decision_outcome = decide(user, doc)            # (True, "allowed") sentinel
  filter = AccessPolicyFilter(
    allowed_departments={actor.department, "ALL"},
    minimum_clearance=clearance_enum.name,
    decision_outcome=decision_outcome,
  )

EMBED (M7):
  embedding = embedder.embed(query_text)
  if len(embedding) not in {1024, 1536}: raise AccessDecisionUnavailableError

DENSE RETRIEVE (M8):
  candidates_dense = await dense_retriever.retrieve(query, embedding)

BM25 RETRIEVE (M8):
  candidates_bm25 = await bm25_retriever.retrieve(query)

RRF FUSE (PURE):
  if not candidates_dense and not candidates_bm25: raise EmptyRetrievalError
  fused = fuse(dense_ranked, bm25_ranked, k=60)

RERANK (M8; OPTIONAL):
  if reranker is not None: ranked = await reranker.rerank(query, fused_ranked, top_n)

POST-RERANK DROP (M0):
  for each ranked candidate:
    doc_projection = candidate.document_projection
                 or documents_by_chunk_id(candidate.chunk_id)
    if doc_projection is None: survivors.append(candidate)        # defer to M9
    elif decide(user, doc_projection).allowed: survivors.append(candidate)
```

---

## Verification

```text
.venv\Scripts\python.exe -m pytest -q tests/domain/retrieval
6 passed, 0 failed, 0 skipped

.venv\Scripts\python.exe -m pytest -q tests/application/retrieval
6 passed, 0 failed, 0 skipped

.venv\Scripts\python.exe -m pytest -q tests/infrastructure/retrieval
3 passed, 0 failed, 0 skipped

.venv\Scripts\python.exe -m pytest -q   # combined
118 passed, 52 skipped, 0 failed   # was 103 at M7 follow-up closure; net +15 from M8
```

### Structural guards

- AST scan of `src/application/retrieval/`: zero `fastapi` / `pydantic` / `uvicorn` / `asyncpg` / `psycopg` / `sqlalchemy` / `langgraph` / `llama_index` import statements.
- AST scan of `src/domain/ports/retrieval.py` and `src/domain/retrieval/rrf.py`: zero framework imports. RRF is pure-Python. The protocols raise no framework dependencies.
- AST scan of `src/infrastructure/retrieval/`: zero `fastapi` / `pydantic` / `asyncpg` import statements; the in-memory adapters are pure Python.
- The application package `src/application/retrieval/` imports only stdlib, intra-application (auth, audit_event), and domain ports. It does NOT import the framework adapters under `src/infrastructure/retrieval/`.

### Typed-state defensive checks

- `RetrieveAuthorizedCandidates` on blank `query_text` raises `AccessDecisionUnavailableError`.
- `RetrieveAuthorizedCandidates` on zero-candidate dense + bm25 raise `EmptyRetrievalError`.
- `_clearance_from_str` on blank string returns `None`; orchestrator short-circuits with `(False, "missing_user_clearance")` decision.
- `_clearance_from_str` on lowercase JWT string (`"internal"`) translates to `Clearance.INTERNAL` case-insensitively.
- A malformed embedding (length not in `{1024, 1536}`) raises `AccessDecisionUnavailableError`.
- The post-rerank drop persists `document_projection` on the rebuilt candidate for observability rows.

### Access-decision integration guarantees

- The orchestrator's pre-filter projection is the M0 pure function. The dense + BM25 SQL `WHERE` clauses (or in-memory predicate) translate the typed projection without re-implementing the decision.
- The orchestrator's post-rerank drop invokes the M0 pure function once per candidate. Every failing candidate is dropped.
- The orchestrator never raises a deny to the caller for an access-decision failure — it returns the typed `AuthorizationOutcome(allowed=False, reason=...)` with `ranked=tuple()` and `stats.zeros()` so the M9 workflow boundary can audit and translate the outcome.

---

## Architectural decisions (review)

- The four mandatory retrieval stages (Dense, BM25, RRF, Rerank) are present and exercised in tests. The guardrail "no shortcuts" in `AGENTS.md` (Architectural Guardrails) is preserved.
- `AccessPolicyFilter` is the single typed projection of the M0 decision for SQL filter use. The adapters do not re-implement the rule; they translate the typed projection into a predicate. A future capability-based swap (hosted pgvector, hosted pg_search) replaces the in-memory adapter without changing the orchestrator or the application surface.
- RRF is a pure function in `src/domain/retrieval/rrf.py`. It is framework-free and shape-stable. The 6 RRF tests pin the deterministic tie-break behavior so the future pgvector / pg_search adapters can match.
- The application-boundary discipline (`repositories -> application -> domain`) is preserved. The orchestrator depends only on the protocols, the cross-application interfaces (auth, audit_event), and the domain ports.
- The M3/M5/M6/M7 launch contract is unchanged. `/health`, `/openapi.json`, `/docs`, `/redoc` continue to be the API boundary. **No** new `/v1/...` endpoint lands at M8.

---

## Findings raised during M8

| ID | Tag | Title | Status |
|---|---|---|---|
| F-39 | LOW | M8 ships cosine-similarity dense and BM25 lexical algorithms as the canonical V1 in-memory implementations. The production pgvector / pg_search adoption is the M12+ milestone (where the in-memory adapters are replaced). The algorithms chosen match ParadeDB defaults so the future SQL translation is direct. | Accepted-Low. Documented in this report. |
| F-40 | LOW | The post-rerank drop re-builds `RetrievalCandidate` to attach `document_projection` for observability. `RetrievalCandidate` is a frozen dataclass so the rebuild is a fresh allocation per survivor. The cost is negligible at `top_n` <= 8 (M9 production cap); a hot-path optimization (mutating the candidate or caching the projection) lands at the framework-adapter layer. | Accepted-Low. Documented in this report. |

---

## Out of scope (deferred)

- No `/v1/query` or `/v1/retrieve` endpoint. M9 wires the orchestrator onto the M9 route surface; the M8 launch contract remains DB-free.
- No real pgvector / pg_search adoption. The in-memory adapters are the V1 written surface; the SQL adapters land in their own milestone.
- No real cross-encoder reranker. The `IdentityReranker` is the V1 stub; the hosted-reranker adoption is open question D-003.
- No per-stage observability row writes. `RetrievalStageStats` is captured in the result; the `retrieval_logs` row writes land at M12.
- No retrieval-time re-embedding of stored chunks. The chunk embeddings from M7 are reused as-is.
- No real Embedding Model SDK. M7's `DeterministicHashEmbeddingModel` is the V1 stub; the Embedding Model capability is open question D-002.

---

## Next milestone

M9 — Workflow Wiring with Citations. The M8 orchestrator is bound onto the M6 LangGraph skeleton; the citation-verification step (the third invocation of the M0 pure function per `AGENTS.md` Architectural Guardrails) lands at this milestone. The M0 decision invocations are: pre-retrieval projection (M8), post-rerank drop (M8), and citation verification (M9).
