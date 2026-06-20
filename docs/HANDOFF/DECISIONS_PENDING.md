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

- **Context**: M2 introduces repository ports (interfaces) the
  domain layer consumes. AGENTS.md and ARCHITECTURE.md require
  the domain layer to remain framework-free.
- **Options**:
  - `src/domain/ports/` (one folder per consumer-facing interface).
  - `src/domain/repositories/` (one folder per V1 table
    repository).
  - Co-located with each domain entity (for example,
    `src/domain/users/repo.py`).
- **Recommendation**: `src/domain/ports/` for the protocol /
  abstract base, with adapters under
  `src/infrastructure/repositories/{in_memory,postgres}/`.
  Mirrors the architecture's layered boundary: domain defines
  contracts; infrastructure provides adapters.
- **Status**: Open.
- **Blocking**: M2 (Repositories).

### D-016 — Repository async surface

- **Context**: The repository layer can be sync, async, or both.
  M2's consumers include M6 (LangGraph) which is async-first,
  and M3 (FastAPI) which is also async. Sync repositories are
  easier to test and reason about but require an async wrapper
  at LangGraph adoption.
- **Options**:
  - All sync. Wrapped at M6 if needed.
  - All async. Tests use `pytest-asyncio` or `asyncio.run`.
  - Mixed: sync repositories with an async wrapper at the
    infrastructure boundary.
- **Recommendation**: All sync repositories. Tests stay simple,
  FastAPI is invoked with `run_in_threadpool` where applicable,
  LangGraph at M6 wraps in async. This matches the M0 pattern:
  the pure access decision is sync and pure; the V1 codebase
  consistently prefers synchronous logic for testability.
- **Status**: Open.
- **Blocking**: M2 (Repositories).

### D-017 — Postgres driver for the M2 Postgres adapter

- **Context**: The M2 Postgres adapter needs a Python driver.
  AGENTS.md forbids introducing ORM dependencies silently
  (Alembic, SQLAlchemy, dbmate, yoyo-migrations are explicitly
  excluded by ADR-0003); the driver is a separate concern.
- **Options**:
  - `psycopg[binary]` 3.x (modern, sync, well-supported).
  - `asyncpg` (async-native, high performance, but the driver
    surface differs from `psycopg`).
  - `psycopg2-binary` (older; widely deployed).
- **Recommendation**: `psycopg[binary]` 3.x (sync). Combined
  with the sync-repository choice in D-016, this keeps the M2
  Postgres adapter consistent with the existing `infrastructure/
  migrations/{apply,rollback}.sh` style: synchronous, no extra
  abstraction layer, no ORM. The driver is added as a
  `pyproject.toml` dependency only after this D-Id is approved.
- **Status**: Open.
- **Blocking**: M2 (Repositories, Postgres half).

### D-018 — Parity test shape (in-memory vs Postgres)

- **Context**: M2 requires the same test matrix to run against
  the in-memory and Postgres adapters. The shape of the parity
  test affects how future repository additions stay
  parity-equivalent.
- **Options**:
  - Parametrize over an adapter factory (single parametrized
    test, two implementations).
  - Mirror-file tests (separate files, shared fixtures).
  - Fixture-based pytest plugin with automatic adapter
    registration.
- **Recommendation**: Parametrize over an adapter factory in
  `tests/infrastructure/repositories/conftest.py` — minimal,
  readable, and forces every test to declare an adapter.
  No new pytest plugin.
- **Status**: Open.
- **Blocking**: M2 (Repositories).

### D-019 — M2 repository list

- **Context**: `PROJECT_STATUS.md` M2 says "every operation
  used by later phases has a passing test." The list of
  repositories must be derived from `WORKFLOWS.md` and
  `POLICIES.md`, not assumed from common RAG patterns.
- **Working list** (from `WORKFLOWS.md` step 14 and
  `POLICIES.md` Logging/Audit):
  - `UserRepository` (load actor by `external_subject`; used by
    M5 JWT, M7 ingestion, M8 retrieval).
  - `AuditLogRepository` (write audit rows; used by M4 audit
    infrastructure).
  - `RetrievalLogRepository` (write retrieval logs;
    `candidate_counts` JSON shape is open per `KNOWN_ISSUES.md`
    I-007).
  - `DocumentRepository` (read V1 documents; used by M8 retrieval
    filter, M7 ingestion).
  - `ChunkRepository` (read V1 chunks; used by M8 retrieval,
    M7 ingestion lifecycle).
  - `EvaluationResultRepository` (write per-case evaluation
    outcomes; used by M13).
  - `IngestionRecordRepository` (record incremental-ingestion
    outcomes; used by M7).
- **Recommendation**: Adopt the working list above. Confirm
  before M2 begins; the assistant will surface additional ports
  if a consumer (M3+) needs them.
- **Status**: Open.
- **Blocking**: M2 (Repositories).

---

## Approved

(none yet)

---

## Rejected

(none yet)
