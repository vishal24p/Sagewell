# M7 Closure — Ingestion (LlamaIndex, idempotent on content_checksum)

**Date**: 2026-06-26
**Milestone**: M7 — Ingestion.
**Scope**: an in-process `IngestDocument` use case wired to a LlamaIndex-backed `DocumentChunkerProtocol` and a deterministic-hash `EmbeddingModelProtocol`. Idempotent on `documents.content_checksum`. Replaced chunks are not searchable (`status='retired'`). Job outcome is recorded in `audit_logs` through M4's `RecordAuditEvent`. **No** background worker, **no** `/v1/*` route at M7; the use case is exercised in-process.
**Status**: **CLOSED 2026-06-26** on `feat/m7-ingestion`.
**Closure artifact**: this file plus the application / infrastructure / tests tree.

---

## Decision IDs Locked (this milestone)

| D-ID | Decision |
|---|---|
| D-052 | M7 ships `src/application/ingestion/` as a fourth application-package sibling to `audit_event/`, `auth/`, and `workflow/`. The package owns the `IngestDocument` use case, the typed `IngestDocumentCommand` / `IngestDocumentResult` / `IngestOutcome` projections, and the typed-error hierarchy (`IngestionDomainError` -> `IngestionPipelineError`, `MissingContentError`, `EmbeddingShapeMismatchError`). |
| D-053 | M7 introduces two new framework-free protocols in `src/domain/ports/ingestion.py`: `DocumentChunkerProtocol` (returns `Sequence[ChunkSegment]`) and `EmbeddingModelProtocol` (returns `list[float]` of length `EMBEDDING_DIM = 1536`). The application package imports the protocols only; the concrete LlamaIndex-backed chunker and the deterministic-hash embedder live under `src/infrastructure/ingestion/`. |
| D-054 | M7 widens the application-side repositories with two new write methods: `DocumentRepository.upsert_by_source(DocumentUpsertCommand) -> DocumentUpsertResult` and `ChunkRepository.replace_for_document(document_id, Sequence[ChunkDraft]) -> ChunkReplaceResult`. The Postgres adapter runs both writes inside a transaction so a mid-call failure cannot leave partially active rows. |
| D-055 | `IngestDocument` is idempotent on `documents.content_checksum`. The same content re-issued against the same `(source_system, source_id)` returns `IngestOutcome.SKIPPED` and emits one `RecordAuditEvent` row carrying `reason_code = "ingestion_skipped"`. A different `content_checksum` updates the row in place + retires the previously active chunks for the document_id + inserts the freshly-chunked drafts; the use case emits one `ingestion_succeeded` row. A pipeline failure (`IngestionDomainError`, `PersistenceError`, or any non-typed exception) emits one `ingestion_failed` row and raises `IngestionPipelineError` for the caller. |
| D-056 | The three new reason codes (`ingestion_succeeded`, `ingestion_skipped`, `ingestion_failed`) extend the `_ALLOWED_REASON_CODES` predicate. The strict `ReasonCode` Literal stays narrowed to the seven M0 codes; the access-decision output shape is preserved. The application package continues to import the predicate from `src.domain.ports.reason_codes`. |
| D-057 | Dependency surface widens: `llama-index-core>=0.13,<0.15` is added to `pyproject.toml`'s runtime dependencies. The chunker adapter pulls `SentenceSplitter` lazily so a sandbox without LlamaIndex does not pay the import cost at module load. M7 does NOT commit to a specific embedding provider; the `DeterministicHashEmbeddingModel` is the M7 stub and the Embedding Model capability is decision-deferred per the open question D-002. |
| D-058 | The M3/M5 API surface is unchanged at M7. `/health`, `/openapi.json`, `/docs`, `/redoc` continue to be the API boundary. M7 introduces **no** `POST /v1/ingest` endpoint. The use case is exercised through tests; future ingest endpoints (if introduced) live under a separate M7-extension milestone so the launch contract stays DB-free. |
| D-059 | The content-checksum normalization function `normalize_content_checksum(text)` (`src/application/ingestion/checksum.py`) strips `\r\n` to `\n`, collapses 3+ blank lines, trims trailing whitespace per line, and hashes with sha256 over the resulting UTF-8 bytes. The same content with Windows / Unix / Mac line endings yields the same checksum. |
| D-060 | M7 widens the application-package import boundaries. `src/application/ingestion/` imports only stdlib, intra-application (`audit_event`, `auth`), domain ports, and `src/infrastructure/repositories/` — never `src/infrastructure/ingestion/`, never `src/infrastructure/langgraph/`. The framework adapters live below the application boundary; the application depends only on the protocols they implement. |

---

## Files Created Under M7

### Source

- `src/application/ingestion/__init__.py` — package surface (re-exports).
- `src/application/ingestion/ingest.py` — `IngestDocument` use case + `IngestDocumentCommand` / `IngestDocumentResult` / `IngestOutcome`.
- `src/application/ingestion/errors.py` — typed-error hierarchy.
- `src/application/ingestion/checksum.py` — `normalize_content_checksum` helper.
- `src/domain/ports/ingestion.py` — `DocumentChunkerProtocol`, `EmbeddingModelProtocol`, `ChunkSegment`.
- `src/infrastructure/ingestion/__init__.py` — adapter surface.
- `src/infrastructure/ingestion/chunker.py` — `LlamaIndexChunker`, `LlamaIndexChunkerConfig`.
- `src/infrastructure/ingestion/embedding.py` — `DeterministicHashEmbeddingModel`.

### Tests

- `tests/application/ingestion/conftest.py` — `FixedSizeChunker`, `DeterministicHashEmbedder` (test-only stubs), `record_audit_event`, `actor`/`document_repo`/`chunk_repo`/`audit_repo` fixtures, `make_cmd` factory.
- `tests/application/ingestion/test_ingest_document.py` — six tests: happy path, idempotence, replace-on-different-content, chunker failure, blank content, embedding shape mismatch.
- `tests/infrastructure/ingestion/test_ingestion_adapters.py` — four tests: chunker ordinals+metadata, empty-input handling, embedder shape, embedder reproducibility.
- `tests/infrastructure/repositories/test_documents_m7_upsert.py` — five parity tests for `upsert_by_source` + `replace_for_document`.

### Documentation

- `docs/AUDITS/M7_REPORT.md` (this file).
- `docs/AUDITS/FINDINGS.md` — F-36, F-37, F-38 (Low-severity hygiene).
- `MEMORY.md` — M7 closure row + decisions D-052..D-060.
- `docs/AUDITS/AUDIT_HISTORY.md` — row 20.
- `docs/AUDITS/MILESTONE_GATES.md` — M7 row marked Closed.
- `docs/HANDOFF/CURRENT_STATE.md` — M7 row added to Completed.
- `docs/HANDOFF/DECISIONS_PENDING.md` — D-052..D-060 Added to Approved.
- `NEXT_AGENT.md` — flips Current Milestone to M8 (Retrieval with Access Filter).
- `PROJECT_STATUS.md` — flip "State" line; risks row update.

---

## Files Modified Under M7

- `pyproject.toml` — adds `llama-index-core>=0.13,<0.15` to runtime dependencies.
- `src/domain/ports/documents.py` — adds `DocumentUpsertCommand` / `DocumentUpsertResult` / `upsert_by_source`.
- `src/domain/ports/chunks.py` — adds `ChunkDraft` / `ChunkReplaceResult` / `replace_for_document`.
- `src/domain/ports/__init__.py` — documents the M7 ports module.
- `src/domain/ports/reason_codes.py` — adds `INGESTION_SUCCEEDED` / `INGESTION_SKIPPED` / `INGESTION_FAILED` + widens `_ALLOWED_REASON_CODES`.
- `src/infrastructure/repositories/in_memory/documents.py` — implements `upsert_by_source`; allocation uses a per-instance `itertools.count`.
- `src/infrastructure/repositories/in_memory/chunks.py` — implements `replace_for_document`; retired + inserted rows are returned from the writer.
- `src/infrastructure/repositories/postgres/documents.py` — implements `upsert_by_source` via `INSERT ... ON CONFLICT (source_system, source_id) DO UPDATE ... RETURNING *`. A `FOR UPDATE` snapshot inside the same transaction distinguishes (inserted, replaced, unchanged).
- `src/infrastructure/repositories/postgres/chunks.py` — implements `replace_for_document` via single multi-row `INSERT ... RETURNING *` inside a transaction; previously active chunks retire via a single `UPDATE ... status='retired' RETURNING id`.

(No other source files touched. M0/M3/M4/M5/M6 surfaces are preserved.)

---

## Surface

### Public application boundary

```python
# src/application/ingestion/__init__.py re-exports:
IngestDocument                       # use case (async)
IngestDocumentCommand                # typed command dataclass
IngestDocumentResult                 # typed result dataclass
IngestOutcome                        # enum: INGESTED | SKIPPED | FAILED
IngestionDomainError                 # base; code = "ingestion_failed"
IngestionPipelineError               # code = "ingestion_pipeline_error"
MissingContentError                  # code = "missing_content"
EmbeddingShapeMismatchError          # code = "embedding_shape_mismatch"
normalize_content_checksum(text)     # sha256(line-ending-normalized)
```

### Domain ports (framework-free)

```python
# src/domain/ports/ingestion.py
class DocumentChunkerProtocol(Protocol):
    def chunk(self, text: str) -> Sequence[ChunkSegment]: ...

class EmbeddingModelProtocol(Protocol):
    def embed(self, text: str) -> list[float]: ...

@dataclass(frozen=True)
class ChunkSegment:
    ordinal: int
    text: str
    metadata: dict
```

### Infrastructure adapters

```python
# src/infrastructure/ingestion/__init__.py re-exports:
LlamaIndexChunker                    # SentenceSplitter-backed
LlamaIndexChunkerConfig              # chunk_size, chunk_overlap capability
DeterministicHashEmbeddingModel      # 1536-dim hash-backed stub
```

### Outcome contract

```text
IDEMPOTENT (same content_checksum):
  outcome = SKIPPED
  audit row: action="ingestion.completed" reason="ingestion_skipped"

CHANGED (different content_checksum):
  outcome = INGESTED
  audit row: action="ingestion.completed" reason="ingestion_succeeded"
  metadata: inserted_chunk_count, retired_chunk_count,
            was_inserted, was_replaced

PIPELINE FAILURE (chunker / embedder / repo):
  outcome = FAILED (raised as IngestionPipelineError)
  audit row: action="ingestion.failed" reason="ingestion_failed"
  metadata: error_code, error_message, actor_user_id

BLANK CONTENT:
  raises MissingContentError; no audit row.
```

---

## Verification

```text
.venv\Scripts\python.exe -m pytest -q tests/application/ingestion
6 passed, 0 failed, 0 skipped

.venv\Scripts\python.exe -m pytest -q tests/infrastructure/ingestion
4 passed, 0 failed, 0 skipped

.venv\Scripts\python.exe -m pytest -q tests/infrastructure/repositories/test_documents_m7_upsert.py
5 passed, 0 failed, 0 skipped

.venv\Scripts\python.exe -m pytest -q   # combined
101 passed, 52 skipped, 0 failed   # was 86 at M6 / 92 after ports; net +15 from M7
```

### Structural guards

- AST scan ("import-statement-level") of `src/application/**` and `src/domain/**`: zero `fastapi` / `pydantic` / `uvicorn` / `asyncpg` / `psycopg` / `sqlalchemy` / `langgraph` / `llama_index` import statements.
- AST scan confirms `llama_index` lives ONLY under `src/infrastructure/ingestion/chunker.py`.
- AST scan confirms `langgraph` lives ONLY under `src/infrastructure/langgraph/workflow.py` (unchanged from M6).
- AST scan confirms `asyncpg` lives ONLY under `src/infrastructure/repositories/postgres/**` (unchanged from M2).
- The application package `src/application/ingestion/` imports only stdlib, intra-application (`audit_event`, `auth`), and domain ports. It does NOT import the framework adapters under `src/infrastructure/ingestion/`.

### Typed-state defensive checks

- `IngestDocument` on blank content raises `MissingContentError`.
- Embedder returning wrong-length vector raises `EmbeddingShapeMismatchError` -> wrapped audit row -> `IngestionPipelineError` raised.
- Chunker raising any non-typed exception is caught -> failure audit row -> `IngestionPipelineError` raised.
- Re-running the same content against the same key yields `SKIPPED` and emits an `ingestion_skipped` audit row.
- Re-running with a different content_checksum updates the row + retires previously active chunks; replaced chunks no longer return from `find_active_by_*`.

### Postgres transaction guarantees (M2 plus M7)

- `upsert_by_source` uses `INSERT ... ON CONFLICT ... DO UPDATE` inside `FOR UPDATE` snapshot -> atomic per key.
- `replace_for_document` runs the retire UPDATE + the multi-row INSERT inside a single `conn.transaction()`. A mid-call failure rolls back side-effects entirely; a clean run retires the prior active chunks and inserts the new set.

---

## Architectural decisions (review)

- M7 introduces an additional application-package sibling (`src/application/ingestion/`). It does not break the D-028 forward-hook rule: `src/api/` does NOT depend on this package. The dependency direction remains `infrastructure -> application -> domain`.
- The `DeterministicHashEmbeddingModel` is capability-shaped and live-replaceable. When the Embedding Model capability lands in a future M8/M11 milestone, the production wiring (the future __main__ / runtime hook) swaps the implementation; the application package does not change.
- The use case keeps `IngestOutcome` as a typed enum so the future M8 / M9 ingest endpoint can switch on the outcome without handling three different exception types.
- `IngestionPipelineError` carries a stable `code` slug (`"ingestion_pipeline_error"`) so M9 / M12 observability rows that grep on the slug catch every translation list.

---

## Findings raised during M7

| ID | Tag | Title | Status |
|---|---|---|---|
| F-36 | LOW | M7 introduces the deterministic-hash embedding stub as a placeholder pending the Embedding Model capability. The stub is reproducible; the same text yields the same vector across calls. Production-shaped embeddings land at the milestone that adopts the Embedding Model capability (open question D-002). | Accepted-Low. Documented in this report. |
| F-37 | LOW | M7 widens `src/domain/ports/reason_codes.py`'s `_ALLOWED_REASON_CODES` predicate with three codes (`ingestion_succeeded`, `ingestion_skipped`, `ingestion_failed`). The `ReasonCode` Literal stays narrowed to the seven M0 codes because the access-decision pure function's output shape is preserved; the predicate accumulates the V1 application's full allowed-codes set across milestones. New V1 codes continue to extend the predicate, not the literal (D-044 carried forward). | Accepted-Low. Documented in this report. |
| F-38 | LOW | The `IngestionDomainError.code` slug equals `"ingestion_failed"` by default — every concrete subclass (`IngestionPipelineError`, `MissingContentError`, `EmbeddingShapeMismatchError`) overrides the slug so audit row `metadata["error_code"]` carries a stable app-domain-side identifier. Tests assert on the slug, not on the message text. | Accepted-Low. Documented in this report. |

---

## Out of scope (deferred)

- No background worker / scheduler / queue. M7 ingestion runs in-process.
- No `/v1/ingest` endpoint. The launch contract stays DB-free; the use case is exercised through tests.
- No real Embedding Model SDK. The stub lives until the capability is adopted; M7 deliberately keeps that decision open.
- No chunking-policy autodetection. LlamaIndex's `SentenceSplitter` (M7 default) is the canonical chunker; a future M7-extension or M8 milestone may swap to LlamaIndex's `SemanticSplitter` (also a llama-index-core dependency). The chunker is configurable via `LlamaIndexChunkerConfig` so the swap is local to the adapter.
- No return to the M3/M5 `/v1/...` route surface. M7 introduces zero reversal of the D-028 forward-hook rule.
- No retrieval / search hydration at M7. The M8 stages (dense, BM25, RRF, cross-encoder) operate over the chunks inserted here.

---

## Next milestone

M8 — Retrieval with Access Filter. Every retrieval adapter (pgvector dense, pg_search BM25, RRF fusion, cross-encoder rerank) lands in this milestone, paired with the access-decision pure function from the first test. The pre-retrieval SQL filter and the post-rerank drop are exercised as part of M8, not as a separate phase. The M7-ingested chunks are the dataset the M8 stages consume.
