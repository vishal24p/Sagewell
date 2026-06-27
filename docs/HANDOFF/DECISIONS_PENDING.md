# Decisions Pending

This file tracks decisions that require human approval before
implementation. Status values: **Open**, **Approved**, **Rejected**.

When a decision is approved, move it to `MEMORY.md` as an accepted
decision. When it is rejected, archive it in this file under
"Rejected."

---

## Open

### D-001 — JWT signing algorithm and key management (long-term)

- **Context**: V1 uses JWT for authentication. The specific
  algorithm (HS256, RS256, EdDSA, etc.), the key source, the key
  rotation policy, and the key distribution mechanism are not
  pinned for the long term.
- **M5 carve-out** (already approved, see `## Approved` below):
  HS256 + shared secret from `SAGEWELL_JWT_SECRET`.
- **Options**:
  - Keep HS256 indefinitely (rotates via restart).
  - Switch to RS256 with public key fetched from a JWKS
    endpoint.
  - EdDSA with public key fetched from a JWKS endpoint.
  - Federated keying through an external KMS / HSM.
- **Recommendation (deferred)**: revisit at the point M5+
  introduces multi-service verification or rotation without
  service restart. M5 is HS256-only; this entry is the
  forward ADR placeholder.
- **Status**: Open.
- **Blocking**: any future milestone that needs asymmetric
  crypto or non-restart rotation.

### D-002 — Embedding Model capability

- **Context**: V1 uses a capability-based reference to an Embedding
  Model. The specific capability (dimensions, max input tokens,
  language support, latency profile) is not pinned.
- **Options**:
  - Capability: dense embedding of 1024-1536 dimensions, English,
    max input 8192 tokens, batch latency under 200ms at 100
    queries per second.
  - Capability: dense embedding of 384-768 dimensions, English,
    max input 512 tokens.
  - Other.
- **Recommendation**: 1024-1536 dimensions, English, max input
  8192 tokens. This matches the production-grade embedding models
  most commonly used in enterprise RAG.
- **Status**: Open.
- **Blocking**: M7 (Ingestion), M8 (Retrieval).

### D-003 — Reranker Model capability

- **Context**: V1 uses a capability-based reference to a Reranker
  Model. The specific capability is not pinned.
- **Options**:
  - Capability: cross-encoder reranker, English, max query 512
    tokens, max document 512 tokens, batch latency under 100ms at
    100 candidates.
  - Capability: cross-encoder reranker, English, larger context.
  - Other.
- **Recommendation**: Cross-encoder reranker with the stated
  limits. Larger contexts are unnecessary for the chunk sizes
  produced by LlamaIndex semantic chunking in V1.
- **Status**: Open.
- **Blocking**: M8 (Retrieval, stage 4).

### D-004 — Guardrail Model capability

- **Context**: V1 uses a capability-based reference to a Guardrail
  Model. The specific capability is not pinned.
- **Options**:
  - Capability: classify (query, retrieved chunks) as
    `allow | downgrade | refuse`, with rationale, latency under
    300ms.
  - Other.
- **Recommendation**: As stated. Rationale is required so that
  guard verdicts in `audit_logs` are explainable.
- **Status**: Open.
- **Blocking**: M11 (LLM Guard).

### D-005 — Generation Model capability

- **Context**: V1 uses a capability-based reference to a Generation
  Model. The specific capability is not pinned.
- **Options**:
  - Capability: grounded generation with citations, English,
    context window 8192-32768 tokens, structured output for
    citation tuples.
  - Other.
- **Recommendation**: Grounded generation with structured
  citation output. The citation tuple shape is the contract for
  M9 (Workflow Wiring with Citations).
- **Status**: Open.
- **Blocking**: M8 (Retrieval — citation format contract), M9
  (Workflow Wiring).

### D-006 — RAGAS release-gate thresholds

- **Context**: V1 runs RAGAS on every release gate. The numeric
  thresholds for Faithfulness, Context Precision, Context Recall,
  and Answer Relevancy are not pinned.
- **Options**:
  - Pin numeric thresholds now.
  - Run RAGAS as informational until the baseline is established,
    then pin thresholds after M13.
- **Recommendation**: Run RAGAS as informational until the
  baseline is established. Pin thresholds after M13 with a
  follow-up ADR.
- **Status**: Open.
- **Blocking**: M13 (RAGAS Evaluation).

### D-007 — RBAC Access Outcome Suite thresholds

- **Context**: V1 runs the RBAC Access Outcome Suite on every
  release gate. The suite is currently binary (pass / fail per
  case). There is no per-metric threshold because the suite asserts
  access-decision outcomes, not answer strings.
- **Options**:
  - 100% pass required. Any failing case blocks release.
  - Allow N failing cases per release candidate as a temporary
    triage buffer.
- **Recommendation**: 100% pass required. Any failing case blocks
  release. This matches the security-critical nature of the access
  decision.
- **Status**: Open.
- **Blocking**: M13 (RAGAS Evaluation, release gate definition).

### D-008 — Audit log retention policy

- **Context**: V1 stores security-relevant events in `audit_logs`.
  The retention period is not pinned.
- **Options**:
  - 90 days.
  - 1 year.
  - 7 years (regulatory minimum for some industries).
  - Indefinite.
- **Recommendation**: 1 year as the V1 default. This is a
  default; specific deployments can override via configuration.
  Pinned in a separate retention ADR before any production
  deployment.
- **Status**: Open.
- **Blocking**: M12 (Audit and Retrieval Logs complete). Does
  not block M0-M11.

### D-009 — Retrieval log retention policy

- **Context**: V1 stores retrieval logs in `retrieval_logs`. The
  retention period is not pinned.
- **Options**: Same as D-008.
- **Recommendation**: 30 days. Retrieval logs are higher volume
  than audit logs and are used for debugging, not compliance.
  Pinned in the same retention ADR.
- **Status**: Open.
- **Blocking**: M12 (Audit and Retrieval Logs complete). Does
  not block M0-M11.

### D-010 — Evaluation result retention policy

- **Context**: V1 stores evaluation results in
  `evaluation_results`. The retention period is not pinned.
- **Options**: Same as D-008.
- **Recommendation**: 1 year. Evaluation results are used for
  release-gate history and regression tracking. Pinned in the
  same retention ADR.
- **Status**: Open.
- **Blocking**: M12 (Audit and Retrieval Logs complete). Does
  not block M0-M11.

### D-015 — M2 repository port layout

- **Decision (Approved 2026-06-20)**: `src/domain/ports/` for
  the protocol / abstract base, with adapters under
  `src/infrastructure/repositories/{in_memory,postgres}/`.
- **Final layout**: `src/domain/ports/{clearances,reason_codes,errors,users,documents,chunks,audit_logs,retrieval_logs,evaluation_results}.py`.
- **MEMORY.md entry**: 2026-06-20 row "M2 ports layer introduced".

### D-016 — Repository async surface

- **Decision (Approved 2026-06-20)**: All async repository
  methods. Tests use `pytest-asyncio>=0.23,<2.0` with global
  `asyncio_mode = "auto"`.
- **Rationale**: M3 (FastAPI) is async-first. M6 (LangGraph) is
  async-first. Sync would require an async wrapper at every
  boundary. The M2 architecture review confirmed this.
- **MEMORY.md entry**: 2026-06-20 row "M2 ports layer
  introduced" + driver row.

### D-017 — Postgres driver for the M2 Postgres adapter

- **Decision (Approved 2026-06-20)**: `asyncpg` for repository
  drivers, plus `pgvector` 0.4.x to register the pgvector codec
  via `pgvector.asyncpg.register_vector`. (The package name
  `asyncpg-pgvector` does NOT exist on PyPI; the canonical
  `pgvector` package registers itself.)
- **Driver shape**: `src/infrastructure/repositories/postgres/pool.py`.
  JSONB codec also registered in the same `init` callback.
- **MEMORY.md entry**: 2026-06-20 row "M2 repository drivers".

### D-018 — Parity test shape (in-memory vs Postgres)

- **Decision (Approved 2026-06-20)**: Parametrize over an
  adapter factory in `tests/infrastructure/repositories/conftest.py`.
  Postgres tests skip when `SAGEWELL_DB_URL` is unset or
  unreachable.
- **MEMORY.md entry**: 2026-06-20 row "M2 test isolation".

### D-019 — M2 repository list

- **Decision (Approved 2026-06-20)**: Six repositories,
  `IngestionRecordRepository` deferred to M7. The final list:
  `UserRepository`, `DocumentRepository`, `ChunkRepository`,
  `AuditLogRepository`, `RetrievalLogRepository`,
  `EvaluationResultRepository`. No `IngestionRecordRepository`.
- **MEMORY.md entry**: 2026-06-20 row "M2 ports layer
  introduced".

### D-020 — M3 correlation id generator algorithm

- **Decision (Approved 2026-06-20)**: UUID4 (`uuid.uuid4()`).
- **Alternatives considered**: UUIDv7 for sortable ids;
  deterministically-generated id for trace continuity. Decision
  prefers UUID4 because the API skeleton's correlation id is a
  per-request ephemeral generated id without ordering needs.

### D-021 — M3 error envelope shape

- **Decision (Approved 2026-06-20)**: minimum envelope
  `{code, message, correlation_id}`. Nothing extra at M3. Field
  validators enforced; the envelope is identical across every
  error class the skeleton surfaces.

### D-024 — M3 Settings surface

- **Decision (Approved 2026-06-20)**: `SAGEWELL_LOG_LEVEL`,
  `SAGEWELL_API_HOST`, `SAGEWELL_API_PORT` only.
- **Removed**: `SAGEWELL_CORS_ALLOWED_ORIGINS` from M3 scope.
- **Deferred**: `SAGEWELL_DB_URL`, `SAGEWELL_TRUSTED_PROXY_HEADER`,
  CORS, JWT.

### D-025 — Default docs surface

- **Decision (Approved 2026-06-20)**: `/docs`, `/redoc`,
  `/openapi.json` enabled by default.

### D-026 — `__main__.py`

- **Decision (Approved 2026-06-20)**: Keep
  `src/api/__main__.py` so `python -m src.api` is healthy.

### D-027 — Catch-all log keys

- **Decision (Approved 2026-06-20)**: Three keys:
  `correlation_id`, `exception_type`, `exc_message` (renamed
  from the originally-spoken `message` to avoid `LogRecord`'s
  reserved field; semantic content is preserved).

### D-028 — Forward dependency direction for M4+

- **Decision (Approved 2026-06-20)**: `src/api/` MUST NOT
  import any future workflow, retrieval, or generation module.
  The dependency direction is `workflow -> api`, not
  `api -> workflow`. M3 ships with zero such imports; future
  imports run through it.

### D-029 — M4 audit intake surface

- **Decision (Approved 2026-06-20)**: M4 ships the **application
  use case only**. No middleware. No test endpoint. Build the
  application layer cleanly; stop on architectural ambiguity.

### D-030 — M4 reason-codes expansion

- **Decision (Approved 2026-06-20)**: `src/domain/ports/reason_codes.py`
  is unchanged at M4. Only the seven M0 IMM codes are emitted.
  I-001 stays open for the milestone that introduces the wider
  enumeration with real usage context.

### D-031 — M4 dependency-injection shape

- **Decision (Approved 2026-06-20)**: `create_app` accepts
  `audit_repo` as an optional keyword; `__main__.py` owns
  pool construction. The factory does NOT construct a pool,
  does NOT touch `SAGEWELL_DB_URL`, does NOT import asyncpg.

### D-032 — M4 request-time audit writes

- **Decision (Approved 2026-06-20)**: No automatic audit writes
  during requests at M4. The launch contract stays DB-free until
  M5. The audit writer is exercised via tests; future M5+
  consumers invoke it.

### D-033 — `AUDIT_HISTORY.md` row 16 shape

- **Decision (Approved 2026-06-20)**: row 16 is updated (not split)
  to include the M3 docs-alignment commit `debe101` and the
  second push landing. Audit history stays milestone-focused.

### D-034 — `src/api/__init__.py` docstring at M4

- **Decision (Approved 2026-06-20)**: the M3 docstring is
  unchanged at M4. The seam is purely via `create_app`'s
  optional `audit_repo` parameter; no new in-docstring
  cross-layer language is added.

### D-035 — `create_app` signature lock (no `pool` parameter)

- **Decision (Approved 2026-06-20)**: `create_app` keeps exactly
  the `audit_repo` parameter; no `pool` parameter is introduced.
  `__main__.py` owns pool construction. Even `TYPE_CHECKING`-
  gated asyncpg references do not belong at the M4 factory.

### D-036 — Two-error split at M4

- **Decision (Approved 2026-06-20)**: split kept — `AuditEventError`
  is the base; `PersistenceFailure(AuditEventError)` is the
  specific failure signal. Validation and persistence failures
  are different categories.

### D-037 — Implementation sign-off for M4

- **Decision (Approved 2026-06-20)**: proceed with M4
  implementation. The plan and method-signature plan were
  approved at this turn; land code now.

---

## Approved

### D-001 — JWT signing algorithm and key management (Approved 2026-06-21)

- **M5 implementation carve-out (current)**: HS256 only at
  M5. Symmetric, shared secret. Key source:
  `SAGEWELL_JWT_SECRET` environment variable. Required at
  runtime.
- **Long-term question still open**: future ADRs may pin
  RS256 with a JWKS endpoint or an external KMS source.
  See `## Open` D-001 below.

### D-038 — M5 auth application package (Approved 2026-06-21)

- **Path**: `src/application/auth/`. Sibling to
  `src/application/audit_event/`. Owns `VerifyJwtToken`,
  typed-actor projection, typed-failure projection, and the
  HS256 signer. Imports only `src/domain/ports/` and intra-
  application.

### D-039 — M5 JWT middleware at the API boundary (Approved 2026-06-21)

- **Path**: `src/api/middleware/auth.py`. Calls
  `VerifyJwtToken` on every request. Bad/missing tokens
  produce 401 with the M3 error envelope and a
  `RecordAuditEvent` row carrying
  `reason_code = "JWT_INVALID"`.
- **Skip path**: `/health`, `/docs`, `/redoc` only. The
  middleware enforces auth on `/openapi.json` and every
  other route.

### D-040 — M5 authentication semantics and identity
projection (Approved 2026-06-21)

- **Q1 (trust)**: After successful verification, the
  middleware treats the JWT-claimed identity as the
  authoritative actor. No database lookup is performed
  during authentication. Issuing-server-validated
  `sub`, `department`, `clearance`, `role` are projected
  through `VerifyJwtToken` and attached to
  `request.state.actor` for downstream use cases (M6+).
- **Q2 (unknown-user failure actor)**: When authentication
  fails, the `RecordAuditEvent` row uses a typed actor
  carrier with `user_id="unknown-user"`,
  `department="unknown"`, `clearance="unknown"`,
  `role="unknown"` so the row carries the failure without
  claiming identity. The row still carries the request's
  `correlation_id`.
- **Q3 (openapi.json protection)**: Auth middleware
  protects `/openapi.json`. The skip list is
  `{"/health", "/docs", "/redoc"}` only.
- **Boundary rule**: The auth middleware stays a thin
  glue layer. It does NOT do RBAC, retrieval, generation,
  prompt-protection, or session management. It does NOT
  perform any DB call.

### D-045 — M6 workflow application package (Approved 2026-06-21)

- **Path**: `src/application/workflow/`. Sibling to
  `src/application/audit_event/` and `src/application/auth/`.
  Owns the typed-state dataclass and the typed-failure
  hierarchy (`WorkflowDomainError` -> `AnonymousExecutionError`
  -> `IncompleteActorError`). Imports only standard library
  + intra-application + domain ports.

### D-046 — M6 LangGraph framework-adapter layer (Approved 2026-06-21)

- **Path**: `src/infrastructure/langgraph/`. Adapter
  binds the application-typed state to a LangGraph
  StateGraph channel via `build_initial_channel`,
  `from_state_dict`, `to_state_dict`. The only place in
  the project that imports `langgraph`.

### D-047 — M6 typed-state dataclass shape (Approved 2026-06-21)

- **Shape**: frozen `WorkflowState` dataclass. Required:
  `{user_id, department, clearance, role, correlation_id}`.
  Optional: `query: Optional[str]`.
- **Construction**: `WorkflowState.from_actor(actor)` is
  the canonical factory. `__post_init__` raises
  `IncompleteActorError` on any blank required field,
  bounding direct-constructor misuse.

### D-048 — M6 application entrypoint (Approved 2026-06-21)

- **Signature**: async `run_workflow(state: WorkflowState) -> WorkflowState`.
  Rejects non-`WorkflowState` input with `IncompleteActorError`.
- **Skeleton graph**: `START -> noop_node -> END`. The
  noop node returns the channel unchanged. Future M7+
  milestones replace `noop_node` with V1 retrieval /
  reranking / generation / guard nodes.

### D-049 — M6 application-package import-graph invariants (Approved 2026-06-21)

- **Rule**: The workflow package MUST NOT import
  `src/api/`, `src/infrastructure/`, `fastapi`,
  `pydantic`, `uvicorn`, `asyncpg`, `psycopg`,
  `sqlalchemy`, or any framework SDK. Verified by an
  AST-based import-statement scan over `src/application/`
  and `src/domain/`.

### D-050 — M3/M5 API route surface unchanged at M6 (Approved 2026-06-21)

- **Surface**: `/health`, `/openapi.json`, `/docs`,
  `/redoc` continue to be the API boundary.
- **No `/v1/*` at M6**: the M6 milestone deliberately does
  NOT mount a `/v1/*` endpoint; the `/v1/*` endpoint lands
  at the milestone that wires the V1 retrieval / guards /
  generation pipeline.

### D-051 — M6 dependency pin (Approved 2026-06-21)

- **Pin**: `langgraph>=0.4,<0.6`. The range matches the
  V1 "no version pinning beyond the major-minor pair"
  pattern. M6 does NOT commit to any future
  `langgraph-prebuilt` / `langgraph-checkpoint` adoption;
  M9+ may introduce them.

### D-052 — M7 ingestion application package (Approved 2026-06-26)

- **Path**: `src/application/ingestion/`. Sibling to
  `src/application/audit_event/`, `src/application/auth/`,
  and `src/application/workflow/`. Owns the `IngestDocument`
  use case, the typed `IngestDocumentCommand` /
  `IngestDocumentResult` / `IngestOutcome` projections,
  the typed-error hierarchy
  (`IngestionDomainError` -> `IngestionPipelineError`,
  `MissingContentError`, `EmbeddingShapeMismatchError`),
  and the `normalize_content_checksum` helper. Imports
  only stdlib + intra-application + domain ports; never
  any framework adapter.

### D-053 — M7 chunker / embedder ports (Approved 2026-06-26)

- **Path**: `src/domain/ports/ingestion.py`. New
  framework-free protocols
  (`DocumentChunkerProtocol`, `EmbeddingModelProtocol`)
  carrying `Sequence[ChunkSegment]` and `list[float]
  of length EMBEDDING_DIM`. Application-package
  imports the protocols only; concrete adapters live
  under `src/infrastructure/ingestion/`.

### D-054 — M7 repository write methods (Approved 2026-06-26)

- **Additions**: `DocumentRepository.upsert_by_source`
  returning `DocumentUpsertResult` (with
  `was_inserted` / `was_replaced` / `was_unchanged`
  flags), and `ChunkRepository.replace_for_document`
  returning `ChunkReplaceResult` (retired_chunk_ids
  + inserted_chunks). Postgres adapter runs both
  writes inside a transaction so mid-call failures
  cannot leave partially active rows.

### D-055 — M7 `IngestDocument` outcome contract (Approved 2026-06-26)

- **Outcomes**:
  - `IngestOutcome.SKIPPED` for same content_checksum
    on the same `(source_system, source_id)` key;
    audit row reason code is `ingestion_skipped`.
  - `IngestOutcome.INGESTED` for the path that
    retires prior chunks and inserts the freshly-
    chunked drafts; audit row reason code is
    `ingestion_succeeded`. The row's metadata carries
    `inserted_chunk_count`, `retired_chunk_count`,
    `was_inserted`, `was_replaced`.
  - `IngestOutcome.FAILED` (translated to raised
    `IngestionPipelineError`) when the pipeline raises
    any typed or untyped exception; audit row
    reason code is `ingestion_failed`.

### D-056 — M7 reason-code widening in the predicate only (Approved 2026-06-26)

- **Rule**: `_ALLOWED_REASON_CODES` widens with three
  ingestion outcome codes
  (`ingestion_succeeded`, `ingestion_skipped`,
  `ingestion_failed`). The `ReasonCode` Literal stays
  narrowed to the seven M0 codes because the
  access-decision pure function's output shape is
  preserved. The M5 / D-044 rule is carried forward
  unchanged.

### D-057 — M7 dependency surface (Approved 2026-06-26)

- **Pin**: `llama-index-core>=0.13,<0.15`. The range
  matches the V1 "no version pinning beyond the
  major-minor pair" pattern. The LlamaIndex chunker
  import is lazy so a sandbox without LlamaIndex does
  not pay the import cost at module load. The
  Embedding Model SDK is intentionally not pinned at
  M7; open question D-002 is the canonical
  capability-deferred entry.

### D-058 — M3/M5/M6 route surface unchanged at M7 (Approved 2026-06-26)

- **Rule**: `/health`, `/openapi.json`, `/docs`,
  `/redoc` continue to be the API boundary. M7 ships
  zero `/v1/...` routes. The `IngestDocument` use
  case is exercised through tests; the launch
  contract `uvicorn src.api.app:create_app
  --factory` continues to work DB-free.

### D-059 — M7 content-checksum normalization (Approved 2026-06-26)

- **Algorithm**: strip CRLF/CR to LF, collapse 3+
  blank lines to a single blank line, trim trailing
  whitespace per line, sha256-hex over the resulting
  UTF-8 bytes. The same content with Windows / Unix
  / Mac line endings yields the same checksum. The
  helper is parametrized by `hash_fn` so tests may
  inject a deterministic stub.

### D-060 — M7 application-layer import-graph invariants (Approved 2026-06-26)

- **Rule**: `src/application/ingestion/` imports only
  stdlib, intra-application (`audit_event`, `auth`),
  and `src/domain/ports/`. The package does NOT
  import anything under `src/api/`,
  `src/infrastructure/`, fastapi, pydantic, uvicorn,
  asyncpg, psycopg, sqlalchemy, langgraph, or any
  framework SDK. Verified by an AST-based
  import-statement scan.

### D-015 — M2 repository port layout (Approved 2026-06-20)

- **Final layout**: `src/domain/ports/`.

### D-016 — Repository async surface (Approved 2026-06-20)

- **Final shape**: All async. `pyproject.toml` adds
  `pytest-asyncio>=0.23,<2.0` and sets global
  `asyncio_mode = "auto"`.

### D-017 — Postgres driver for the M2 Postgres adapter (Approved 2026-06-20)

- **Final driver**: `asyncpg` + `pgvector` (PyPI package;
  NOT a package named `asyncpg-pgvector`).
- **Codec init**: registered in `pool.py` `_init_connection`.

### D-018 — Parity test shape (Approved 2026-06-20)

- **Final shape**: Parametrize over adapter factory in
  `tests/infrastructure/repositories/conftest.py`.

### D-019 — M2 repository list (Approved 2026-06-20)

- **Final list**: Six repositories; `IngestionRecordRepository`
  deferred to M7.

### D-020 — M3 correlation id generator (Approved 2026-06-20)

- **Algorithm**: `uuid.uuid4()`. Pure ASGI middleware reads
  `X-Correlation-ID`; if absent a UUID4 is generated.

### D-021 — M3 error envelope (Approved 2026-06-20)

- **Shape**: `{code, message, correlation_id}`.

### D-024 — M3 Settings surface (Approved 2026-06-20)

- **Fields**: `SAGEWELL_LOG_LEVEL`, `SAGEWELL_API_HOST`,
  `SAGEWELL_API_PORT`. `SAGEWELL_CORS_ALLOWED_ORIGINS` removed.

### D-025 — Default docs surface (Approved 2026-06-20)

- **Defaults**: `/docs`, `/redoc`, `/openapi.json` enabled.

### D-026 — `__main__.py` (Approved 2026-06-20)

- **Final**: `src/api/__main__.py` retained.

### D-027 — Catch-all log keys (Approved 2026-06-20)

- **Keys**: `correlation_id`, `exception_type`, `exc_message`.

### D-028 — Forward dependency direction (Approved 2026-06-20)

- **Rule**: `src/api/` does not import future workflow,
  retrieval, or generation. `workflow -> api`.

### D-029 — M4 audit intake surface (Approved 2026-06-20)

- **Surface**: application use case only. No middleware.
  No test endpoint.

### D-030 — M4 reason-codes expansion (Approved 2026-06-20)

- **Codeset**: unchanged at M4. Only seven M0 IMM codes emitted.

### D-031 — Dependency-injection shape (Approved 2026-06-20)

- **Shape**: `create_app(audit_repo=None)`. `__main__.py`
  owns pool construction. No asyncpg in the api layer.

### D-032 — M4 request-time audit writes (Approved 2026-06-20)

- **Behavior**: launch contract stays DB-free. No automatic
  audit writes during requests at M4. Writer is exercised
  through tests.

### D-033 — AUDIT_HISTORY.md row 16 (Approved 2026-06-20)

- **Shape**: row 16 edited (not split). Includes the M3
  docs-alignment commit `debe101`.

### D-034 — src/api/__init__.py docstring (Approved 2026-06-20)

- **Status**: unchanged at M4. Docstring still describes the
  M3 boundary terms; the M4 seam lives in `app.py`'s
  optional parameter.

### D-035 — create_app signature lock (Approved 2026-06-20)

- **Signature**: `audit_repo` parameter only. No `pool`
  parameter. Even TYPE_CHECKING asyncpg references do
  not belong at the M4 factory.

### D-036 — Two-error split (Approved 2026-06-20)

- **Errors**: `AuditEventError` (base),
  `PersistenceFailure(AuditEventError)` (specific).

---


### D-061 -- M8 retrieval ports (Approved 2026-06-26)

- **Path**: src/domain/ports/retrieval.py. New
  framework-free protocols
  (DenseRetrieverProtocol,
  Bm25RetrieverProtocol,
  RerankerProtocol,
  QueryEmbedderProtocol re-export).
  All async. Application-package imports the
  protocols only.

### D-062 -- M8 AccessPolicyFilter projection (Approved 2026-06-26)

- **Shape**: typed projection carrying
  llowed_departments: tuple[str, ...],
  minimum_clearance: str (V1 canonical
  uppercase ladder step), and
  decision_outcome: tuple[bool, str]. The
  decision is NEVER re-implemented at the
  adapter layer; the projection translates
  into a SQL WHERE clause or in-memory
  predicate.

### D-063 -- M8 RetrievalCandidate document_projection (Approved 2026-06-26)

- **Field**: RetrievalCandidate.document_projection:
  Optional[DocumentProjection]. The post-rerank
  drop reads this field; when None, the drop
  defers to M9 citation verification. The in-memory
  and Postgres adapters populate the projection
  so the orchestrator short-circuits without a
  documents-port round-trip.

### D-064 -- M8 retrieval orchestrator (Approved 2026-06-26)

- **Path**: src/application/retrieval/retrieve.py.
  Wires seven stages: pre-filter projection
  (M0) -> embed (M7) -> dense (M8) -> BM25 (M8)
  -> RRF fuse (pure) -> cross-encoder rerank
  (M8, optional) -> post-rerank drop (M0). The
  flow is fixed; future optimizations land at
  the framework-adapter layer.

### D-065 -- M8 clearance-from-str translation (Approved 2026-06-26)

- **Helper**: _clearance_from_str() translates
  JWT-supplied lowercase clearance strings to
  the V1 uppercase enum. None returned for
  blank input (fail-closed to
  missing_user_clearance). Unrecognized
  non-blank strings raise
  AccessDecisionUnavailableError.

### D-066 -- M8 EmptyRetrievalError rule (Approved 2026-06-26)

- **Rule**: EmptyRetrievalError raised when
  BOTH dense AND BM25 return zero candidates.
  The error carries correlation_id for the
  M12 retrieval_logs row.

### D-067 -- M8 orchestrator never raises on SQL-filter mismatch (Approved 2026-06-26)

- **Rule**: the M8 orchestrator does NOT write
  audit rows directly; M9 wires the audit-write
  step onto the workflow state. The orchestrator
  never raises on a SQL-filter mismatch -- it
  returns typed
  AuthorizationOutcome(allowed=False, reason=...)
  with 
anked=tuple() and stats.zeros().

### D-068 -- M8 in-memory retrieval adapters (Approved 2026-06-26)

- **Path**: src/infrastructure/retrieval/in_memory_dense.py,
  in_memory_bm25.py. Canonical V1 algorithms:
  cosine-similarity (Dense); BM25 with
  k1=1.5, =0.75 (BM25; ParadeDB / pg_search
  defaults). Both honor the AccessPolicyFilter
  projection symmetrically.

### D-069 -- M8 IdentityReranker stub (Approved 2026-06-26)

- **Path**: src/infrastructure/retrieval/identity_reranker.py.
  Sort-and-cap stub. Hosted-reranker capability
  is open question D-003.

### D-070 -- M8 zero new routes (Approved 2026-06-26)

- **Rule**: M3/M5/M6/M7 API route surface is
  unchanged at M8. Zero /v1/... endpoints
  land at M8. M9 wires the orchestrator onto
  the M9 route surface.

### D-071 -- M8 RRF pure function (Approved 2026-06-26)

- **Path**: src/domain/retrieval/rrf.py.
  `fuse(dense_ranked, bm25_ranked, *, k=60)`
  is a pure function. Negative `k` raises
  `ValueError`. Tie-break is deterministic
  by `(document_id ASC, chunk_id ASC)`.


### D-072 -- M9 Citation port (Approved 2026-06-26)

- **Path**: src/domain/ports/citations.py. Typed
  Citation shape (chunk_id, document_id, ordinal,
  quote, optional document_projection). The pure
  function receives the projection directly when
  adapters pre-populate it.

### D-073 -- M9 VerifyCitations orchestrator (Approved 2026-06-26)

- **Path**: src/application/citations/verify.py.
  Async VerifyCitations use case with typed
  VerifyCitationsCommand + VerifyCitationsResult
  + DroppedCitation. Invokes decide(user, document)
  once per citation and never re-implements the rule.

### D-074 -- M9 fail-closed semantics (Approved 2026-06-26)

- **Rule**: Missing actor clearance cascades to
  missing_user_clearance. Missing document cascades
  to missing_document_department or
  missing_document_clearance via the M0 pure
  function. Unrecognized non-blank actor clearance
  raises CitationDecisionUnavailableError (503-class
  at the workflow boundary).

### D-075 -- M9 EmptyCitationsError (Approved 2026-06-26)

- **Rule**: Empty VerifyCitations.execute invocation
  raises EmptyCitationsError (code empty_citations).
  400-class input validation failure.

### D-076 -- M9 RunQueryWorkflow LangGraph (Approved 2026-06-26)

- **Path**: src/infrastructure/langgraph/run_query.py.
  Wires RetrieveAuthorizedCandidates (M8) and
  VerifyCitations (M9) onto a typed LangGraph state
  machine: ingest_query -> retrieve_authorized ->
  verify_citations -> mint_response.
  Constructor-injected dependencies.

### D-077 -- M9 /v1/query route (Approved 2026-06-26)

- **Path**: src/api/routers/query.py. Reads the
  typed AuthActor placed by the M5 JWT middleware;
  builds WorkflowState.from_actor(actor, query=...);
  calls app.state.run_query(state). Missing actor
  returns 401; blank query returns 400; missing
  run_query returns 503. Typed JSON envelope on 200.
  Typed via RunQueryFn Protocol at
  src/api/protocols.py.

### D-078 -- M9 DI seam run_query (Approved 2026-06-26)

- **Path**: create_app(..., run_query=None). Without
  DI the API boots but /v1/query returns 503; with
  DI the route returns 200 + envelope. DB-free launch
  contract preserved.

### D-079 -- M9 OpenAPI route-surface guard (Approved 2026-06-26)

- **Rule**: tests/api/test_openapi.py widens the
  strict M3 guard to /health, /v1/query only.

### D-080 -- M9 D-028 forward-hook preserved (Approved 2026-06-26)

- **Rule**: src/api/routers/query.py imports the
  workflow package; the workflow package does NOT
  import anything under src/api/. Verified by AST
  scan.

### D-081 -- M10 RegexRule ports (Approved 2026-06-26)
### D-082 -- M10 RegexGuard use case (Approved 2026-06-26)
### D-083 -- M10 regex_guard DI seam (Approved 2026-06-26)
### D-084 -- M11 GuardrailVerdict + GuardrailModelPort capability-shaped (Approved 2026-06-26)
  Capability-shaped per open question D-004 (hosted Guardrail Model).
### D-085 -- M11 LLMGuard use case (Approved 2026-06-26)
### D-086 -- M12 RecordRetrievalLog + RecordGuardVerdict use cases (Approved 2026-06-26)
### D-087 -- M12 predicate widens application-controlled set; repository Enum stays narrowed (Approved 2026-06-26)
### D-088 -- M13 RAGAS typed contract + RagasScorerPort capability-shaped (Approved 2026-06-26)
  Capability-shaped per open question D-006 (hosted RAGAS SDK).
### D-089 -- M13 RunRagasCase use case threshold rule (Approved 2026-06-26)
  Threshold rule: every metric in case.minimums (when set) must be at or
  above its threshold; metrics absent from minimums are informational.
### D-090 -- M14 launch-contract release-gate tests (Approved 2026-06-26)
  tests/release_gate/test_m14_hardening.py - 5 tests pinning the DB-free
  launch contract; /v1/query 503 without runner; stub runner envelope;
  M10 Regex Guard refusal; full M-stack smoke.
### D-091 -- M14 RBAC Access Outcome Suite integration through M9 pipeline (Approved 2026-06-26)
  tests/release_gate/test_m14_rbac_suite.py - 7 tests pinning D-007
  100% pass on the canonical RBAC suite end-to-end through the M9 pipeline.
### D-092 -- M14 combined pytest is the canonical V1 release bar (Approved 2026-06-26)
  166 passed, 52 sandbox-skips, 0 failed.
  Future milestones MUST add to (not replace) the release gate.

## Rejected

(none yet)
