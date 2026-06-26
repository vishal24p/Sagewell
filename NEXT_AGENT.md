# NEXT_AGENT

This file is the operational entry point for a new agent. It answers
one question: "what is the next task, and what do I need to know to
do it?"

Read `AGENTS.md` first. Read `docs/HANDOFF/CURRENT_STATE.md` for a
snapshot of progress. Read the files listed under "Relevant
Documents" before doing anything.

---

## Current Milestone

**M8 — Retrieval with Access Filter.**

## Current Status

**M0 closed on 2026-06-19 (commit `a78e21c`). M1 closed on
2026-06-19. M2 closed on `main` at `7849d89`. M3 closed at
`fb110bd`. M4 closed at `03351c4`. All pushed to `origin/main`.
M5 is closed on `feat/m5-jwt-validation` (this repo's remote).
M6 is closed on `feat/m6-langgraph-skeleton`. M7 is closed on
`feat/m7-ingestion`. M8 (Retrieval with Access Filter) is the
next implementation milestone.**

M3 silhouette is the pure API skeleton per the user's reduced
decision (`GET /health`, `GET /openapi.json`, `GET /docs`,
`GET /redoc`).

M4 silhouette:

- `src/application/audit_event/` package with
  `RecordAuditEvent` use case, `RecordAuditCommand` DTO,
  `AuditEventId` newtype, `Clock` Protocol + `SystemClock`,
  `AuditEventError` / `PersistenceFailure(AuditEventError)`.
- 10 distinct passing tests at
  `tests/application/audit_event/test_record_audit_event.py`.
- `src/api/app.py` accepts `audit_repo: Optional[AuditLogRepository]
  = None` (DI seam); `__main__.py` does NOT construct a pool.
- Launch contract `uvicorn src.api.app:create_app --factory`
  remains DB-free.
- Combined pytest: 54 passed, 52 sandbox-skips, 0 failed.

M5 silhouette (closure record at
`docs/AUDITS/M5_REPORT.md`):

- `src/application/auth/` package: `VerifyJwtToken` use case,
  `HS256JwtSigner`, `AuthActor` projection, typed-failure
  hierarchy (`AuthFailure` + `JwtMissing` / `JwtMalformed` /
  `JwtBadSignature` / `JwtExpired` / `JwtInvalid`), and the
  `UNKNOWN_USER_ACTOR` typed failure carrier.
- 10 distinct passing tests at
  `tests/application/auth/`.
- `src/api/middleware/auth.py` is a pure-ASGI JWT validation
  middleware. Skips `{"/health", "/docs", "/redoc"}`. On every
  other path, runs `VerifyJwtToken`. Bad / missing / expired /
  bad-signature tokens return 401 with the canonical
  `{code, message, correlation_id}` envelope and a `RecordAuditEvent`
  row carrying `reason_code="jwt_invalid"` and
  `metadata["auth_failure_carrier"] = "unknown-user"`.
- `__main__.py` reads `Settings.jwt_secret` and constructs an
  `HS256JwtSigner(secret=...)` when set. When unset, the
  launch contract stays DB-free and auth-less.
- `create_app(jwt_signer=...)` is the M5 DI seam. With
  `jwt_signer=None` the middleware mounts but is a no-op.
- Successful verification attaches the typed `AuthActor` to
  `scope["state"]["actor"]` for M6+ consumers (the LangGraph
  state machine).
- Combined pytest: 73 passed, 52 sandbox-skips, 0 failed.
  M0 RBAC still 31/31; M3 tests/api still 13/13; M4
  application tests still 10/10.
- Findings F-31..F-34 surfaced during verification and were
  resolved in this session.

M6 silhouette (closure record at
`docs/AUDITS/M6_REPORT.md`):

- `src/application/workflow/` is the third application
  package, sibling to `src/application/audit_event/` and
  `src/application/auth/`. It owns the frozen
  `WorkflowState` dataclass with required fields
  `{user_id, department, clearance, role, correlation_id}`
  and an optional `query`. The typed factory
  `WorkflowState.from_actor(actor)` is the canonical entry;
  `__post_init__` defends direct constructor use.
- Typed-error hierarchy: `WorkflowDomainError` (base) →
  `AnonymousExecutionError` → `IncompleteActorError`.
- `src/infrastructure/langgraph/workflow.py` binds the
  typed `WorkflowState` to a LangGraph `StateGraph` channel
  shape via `build_initial_channel` (typed → channel) and
  `from_state_dict` (channel → typed). The skeleton graph is
  `START → noop_node → END`; the noop is identity.
- `run_workflow(state)` is the async application entrypoint;
  it rejects non-`WorkflowState` input with
  `IncompleteActorError`.
- Combined pytest: 86 passed, 52 sandbox-skips, 0 failed.
  8 distinct tests at `tests/application/workflow/test_workflow_state.py`
  + 5 at `tests/infrastructure/langgraph/test_workflow.py`.
- The M3/M5 API surface is unchanged at M6: no `/v1/*`
  endpoint. The D-028 forward-hook surface
  (workflow → api, never api → workflow) is preserved.
- Finding F-35 (channel-shape vs typed-state split) raised,
  accepted-Low, and documented in `docs/AUDITS/M6_REPORT.md`.

M7 silhouette (closure record at
`docs/AUDITS/M7_REPORT.md`):

- `src/application/ingestion/` is the fourth application
  package, sibling to `audit_event/`, `auth/`, and `workflow/`.
  It owns the `IngestDocument` use case with typed
  `IngestDocumentCommand` / `IngestDocumentResult` /
  `IngestOutcome` projections.
- Outcome contract: `SKIPPED` (same content_checksum),
  `INGESTED` (retires prior active chunks + inserts fresh
  drafts), `FAILED` (raises `IngestionPipelineError`).
  Each branch emits one audit row through M4's
  `RecordAuditEvent` with the matching reason code.
- `src/domain/ports/ingestion.py` introduces two
  framework-free protocols (`DocumentChunkerProtocol`,
  `EmbeddingModelProtocol`).
- `src/infrastructure/ingestion/chunker.py` ships a
  LlamaIndex `SentenceSplitter`-backed adapter (lazy
  import); `src/infrastructure/ingestion/embedding.py`
  ships the deterministic-hash 1536-dim stub
  (capability-deferred per open question D-002).
- M7 repository writes: `DocumentRepository.upsert_by_source`
  + `ChunkRepository.replace_for_document`. Postgres
  adapter runs both inside `conn.transaction()` so a
  mid-call failure rolls back side-effects entirely.
- `pyproject.toml` adds `llama-index-core>=0.13,<0.15`.
- 15 new tests across `tests/application/ingestion/` (6),
  `tests/infrastructure/ingestion/` (4), and
  `tests/infrastructure/repositories/test_documents_m7_upsert.py` (5).
- Combined pytest: 101 passed (was 86; +15), 52
  sandbox-skips, 0 failed. The M3/M5/M6 API surface is
  unchanged at M7; no `POST /v1/ingest` endpoint lands here.
- Findings F-36..F-38 (capability-deferred embedding
  stub, predicate-vs-Literal reason-code widening,
  typed-error slug defaults) raised and accepted-Low.

---

## Next Task

The current task is to land **M8 — Retrieval with
Access Filter** on a feature branch:

- Four retrieval stages are developed one at a time:
  Dense (pgvector cosine), BM25 (pg_search), RRF fusion,
  cross-encoder rerank.
- Every stage is paired with the access-decision pure
  function from M0 from the first test. Pre-retrieval
  SQL filter and post-rerank drop are exercised as part
  of M8, not as a separate phase.
- The retrieval adapters live under
  `src/infrastructure/retrieval/{dense,bm25,rrf,reranker}/`
  with framework-free ports under `src/domain/ports/`.
- The M7 ingestion use case is the dataset; M8 reads from
  the chunks ingested at M7.

### How to test (M8 prelude)

- `.venv\Scripts\python.exe -m pytest -q tests/api tests/rbac
  tests/infrastructure tests/application` is green.
- `grep -rE "fastapi|pydantic|uvicorn" src/domain/` returns
  zero rows.
- `grep -rE "asyncpg|psycopg|sqlalchemy|llama_index|langgraph"`
  in `src/application/` or `src/domain/` returns zero rows.
  The retrieval ports must import framework-free; framework
  adapters live under `src/infrastructure/retrieval/`.

### How to verify before moving on to M9

- The M7 closure record at `docs/AUDITS/M7_REPORT.md`
  remains accurate.
- The M8 closure record at `docs/AUDITS/M8_REPORT.md`
  carries the four-stage retrieval evidence (dense +
  BM25 + RRF + cross-encoder), the access-decision
  pre-filter + post-rerank drop evidence, and the
  retrieval_logs write-through evidence (the latter
  is M8 partial; the M12 milestone completes the
  retrieval_logs surface).
- Combined pytest stays green; M8 tests add at least
  one test per guarantee above.

---

## Relevant Documents

Read these before starting M8:

- `ARCHITECTURE.md` — Retrieval is hybrid. All four
  stages are mandatory. The access-decision pure function
  is invoked pre-retrieval, post-rerank, and at citation
  verification (the third boundary lands at M9).
- `DATABASE_SCHEMA.md` — V1 tables: `users`, `documents`,
  `chunks` (with `vector(1536)` embedding), `audit_logs`,
  `retrieval_logs`. The M8 dense retrieval adapter targets
  the `chunks_embedding_idx` HNSW index.
- `POLICIES.md` — The access decision is a single pure
  function invoked at every boundary. M8 introduces the
  pre-retrieval boundary + post-rerank boundary.
- `WORKFLOWS.md` — The query-and-answer flow runs
  retrieval stages 6..9 with pre-filter applied; the
  rerank-and-drop step runs at stage 10. M8 covers the
  retrieval side; M9 wires the workflow to mount this.
- `skills/project/retrieval_engine/SKILL.md` — pipeline
  shape, RRF K constant, access-decision enforcement
  points.
- `skills/project/database_design/SKILL.md` — schema and
  index invariants for `documents` and `chunks`.
- `docs/AUDITS/M7_REPORT.md` — confirms the ingestion
  surface that M8 consumes (the chunks inserted by
  M7's `IngestDocument` are the dataset).

---

## Do Not Touch for M8

The M0..M7 "Do Not Touch" lists still apply. Additions for
M8 are NOT prohibitions against working on M8; they are
prohibitions against pre-empting M9+ while working on M8:

- Do NOT introduce a query-time workflow mount on a
  `/v1/*` route. Retrieval is exercised through tests;
  the query-time workflow wiring lands at M9.
- Do NOT pivot the M0 access-decision pure function. M8
  calls the function unchanged.
- Do NOT introduce a vector-index hint or a pgvector
  configuration knob beyond what the M1 schema already
  defines.
- Do NOT introduce streaming, SSE, or WebSocket — V1
  stays request/response.
- Do NOT introduce CORS, OIDC, Okta, Entra ID, LDAP, or
  external IAM. The V1 auth path is JWT-only and unchanged
  from M5.
- Do NOT introduce multi-tenant concepts, ACL tables, or
  group/role authorization. These are out of V1 per
  AGENTS.md.
- Do NOT pin a specific embedding / reranker provider
  in code. The embedding capability stays open question
  D-002; the reranker capability stays open question
  D-003. M8 ships capability-shaped ports.

---

## Do Not Touch for M5

The M0..M4 "Do Not Touch" lists still apply. Additions for
M5 are NOT prohibitions against working on M5; they are
prohibitions against pre-empting M6+ while working on M5:

- Do NOT introduce JWKS or asymmetric crypto. HS256 + shared
  secret only at M5 (D-001).
- Do NOT add a `/v1/*` query-answer endpoint. M5 ships
  `/health` and the JWT-protected error path only; the
  query-answer endpoint lands at M6 (after the LangGraph
  skeleton).
- Do NOT introduce Retrieval / Reranker / LLM / Regex-guard
  coupling. The auth middleware MUST NOT touch retrieval or
  generation.
- Do NOT widen the M0 IMM reason-code set beyond what M5
  actually emits (D-030 carried forward). M5 introduces the
  `JWT_INVALID` reason code through the audit intake; the
  seven M0 codes are unchanged.
- Do NOT introduce streaming, SSE, or WebSocket — V1 stays
  request/response.
- Do NOT introduce CORS, OIDC, Okta, Entra ID, LDAP, or
  external IAM. The V1 auth path is JWT-only.
- Do NOT introduce multi-tenant concepts, ACL tables, or
  group/role authorization. These are out of V1 per
  AGENTS.md.
- Do NOT pivot the auth path away from JWT-claim trust
  (Q1) or weaken the unknown-user failure actor carrier
  (Q2). Adding DB lookups, role-mapping tables, or external
  identity resolution here would re-shape the access
  pipeline and require an ADR.
- Do NOT bind `/openapi.json` to the auth middleware
  differently across environments. M5 enforces JWT on
  `/openapi.json` everywhere by default (Q3); only
  `/health`, `/docs`, and `/redoc` skip the middleware.

---

## M3 Exit Criteria (CLOSED at `fb110bd`)

M3 was closed on 2026-06-20 with the commit `fb110bd`. All
twenty M3 exit criteria are documented in
`docs/AUDITS/M3_REPORT.md` with VERIFIED status. Re-running
the criteria should produce the same outcome — the
repository state is recorded in that report.

## M5-Not-Touch (carry-forward from M0..M4)

The M0..M4 "Do Not Touch" lists still apply. Additions for M5
are NOT prohibitions against working on M5; they are
prohibitions against pre-empting M6+ while working on M5:

- Do NOT introduce JWT validation, even for testing of M0..M4 —
  M5 owns that exemption. Already-implemented M0..M4 code
  paths must work without a JWT.
- Do NOT introduce API-key auth, OAuth, OIDC, Okta, Entra ID,
  LDAP, or any non-JWT auth surface.
- Do NOT add `/v1/*` routes that proxy to retrieval, ranking,
  or generation. M5 ships `/health` + the JWT-protected
  error path only.
- Do NOT add OpenAI/Anthropic/genai SDK dependency — wait
  for M11.
- Do NOT add prompt-protection guard (regex, LLM, etc).
  That belongs to M10/M11.
- Do NOT add streaming or WebSocket — V1 stays request/response.
- Do NOT add CORS configuration beyond what the framework
  needs for the dev `/docs` and `/redoc` UIs.
- Do NOT introduce multi-tenant concepts, ACL tables, or
  group/role authorization. These are out of V1 per
  AGENTS.md.
- Do NOT widen the M0 IMM reason-code set beyond what M5
  actually emits. I-001 stays open.

---

## Known Open Questions

The M0..M2 lists still apply unless resolved. M3 introduces:

- D-020 (Correlation generator algorithm): UUID4 confirmed.
  Carried over as durable decision.
- D-021 (Error envelope shape): fixed
  `{code, message, correlation_id}` for M3.
- D-024 (Settings surface): `SAGEWELL_LOG_LEVEL`,
  `SAGEWELL_API_HOST`, `SAGEWELL_API_PORT` only;
  `SAGEWELL_CORS_ALLOWED_ORIGINS` removed from M3.
- D-025 (Default docs surface): `/docs`, `/redoc`,
  `/openapi.json` enabled by default.
- D-026 (`__main__.py`): kept.
- D-027 (Catch-all log keys): `correlation_id`,
  `exception_type`, `exc_message` only (the third key is
  deliberately spelled `exc_message` to avoid colliding
  with the std-lib `LogRecord` reserved `message` field).
- D-028 (Forward hook): When the application surfaces a
  query-answer handler at M5/M6, it MUST NOT import any
  module under `src/api/`. The pattern is the inverted
  one: the api package depends on the workflow package,
  not the other way around.
- D-029 (M4 audit intake surface): application use case
  only; no middleware; no test endpoint.
- D-030 (Reason-code expansion): unchanged at M4.
  I-001 stays open.
- D-031 (DI shape): `create_app(*, audit_repo=None)`.
  `__main__.py` owns pool construction.
- D-032 (Request-time audit writes): no automatic audit
  writes at M4. Launch contract stays DB-free until M5.
- D-033 (AUDIT_HISTORY row 16): edited (not split) to
  capture the late-state alignment commits.
- D-034 (M3 docstring at M4): unchanged.
- D-035 (create_app signature): `audit_repo` only; no
  `pool` parameter, no TYPE_CHECKING asyncpg.
- D-036 (Two-error split): `AuditEventError` and
  `PersistenceFailure(AuditEventError)` both kept.
- D-037 (M4 implementation sign-off): approved at this
  turn; landing code on main.
- D-038 (M5 auth application package): `src/application/auth/`
  is a dedicated application package, sibling to
  `src/application/audit_event/`. The auth use case
  (`VerifyJwtToken`) and the typed-actor projection live
  there and import only from `src/domain/ports/` plus intra-
  application.
- D-039 (M5 JWT middleware at the API boundary): FastAPI
  middleware in `src/api/middleware/auth.py` performs token
  verification on every request. Bad or missing tokens
  produce 401 with the canonical error envelope and an
  audit row through M4's `RecordAuditEvent`.
 
