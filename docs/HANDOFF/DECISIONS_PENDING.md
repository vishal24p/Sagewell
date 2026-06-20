# Decisions Pending

This file tracks decisions that require human approval before
implementation. Status values: **Open**, **Approved**, **Rejected**.

When a decision is approved, move it to `MEMORY.md` as an accepted
decision. When it is rejected, archive it in this file under
"Rejected."

---

## Open

### D-001 — JWT signing algorithm and key management

- **Context**: V1 uses JWT for authentication. The specific
  algorithm (HS256, RS256, EdDSA, etc.), the key source, the key
  rotation policy, and the key distribution mechanism are not
  pinned.
- **Options**:
  - HS256 with shared secret from environment variable.
  - RS256 with public key fetched from a JWKS endpoint.
  - EdDSA with public key fetched from a JWKS endpoint.
  - Other.
- **Recommendation**: RS256 with JWKS endpoint. Standard
  enterprise pattern, supports rotation without redeploy, supports
  asymmetric verification without distributing private keys.
- **Status**: Open.
- **Blocking**: M5 (JWT Validation).

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

## Rejected

(none yet)
