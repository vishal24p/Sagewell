# NEXT_AGENT

This file is the operational entry point for a new agent. It answers
one question: "what is the next task, and what do I need to know to
do it?"

Read `AGENTS.md` first. Read `docs/HANDOFF/CURRENT_STATE.md` for a
snapshot of progress. Read the files listed under "Relevant
Documents" before doing anything.

---

## Current Milestone

**V1 release-ready. M0..M14 all closed on `feat/m14-hardening`.**

## Current Status

**V1 implementation complete.** M0 closed on 2026-06-19 (`a78e21c`). M1 closed 2026-06-19. M2 closed on `main` at `7849d89`. M3 closed at `fb110bd`. M4 closed at `03351c4`. M5 closed on `feat/m5-jwt-validation`. M6 closed on `feat/m6-langgraph-skeleton`. M7 closed on `feat/m7-ingestion`. M8 closed on `feat/m8-retrieval`. M9 closed on `feat/m9-workflow-citations`. M10 closed on `feat/m10-regex-guard` (Regex Guard). M11 closed on `feat/m11-llm-guard` (LLM Guard capability port). M12 closed on `feat/m12-logs-complete` (audit + retrieval logs). M13 closed on `feat/m13-ragas` (RAGAS capability port). **M14 closed on `feat/m14-hardening` (release-gate tests).** Combined pytest: **166 passed**, 52 sandbox-skips, 0 failed.

**All branches pushed to `origin`** (verified via `git ls-remote --heads origin`). The launch contract boots DB-free end-to-end on `uvicorn src.api.app:create_app --factory` (no audit_repo, no run_query, no regex_guard required).



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

M8 silhouette (closure record at
`docs/AUDITS/M8_REPORT.md`):

- `src/domain/ports/retrieval.py` introduces four
  retrieval ports (`DenseRetrieverProtocol`,
  `Bm25RetrieverProtocol`, `RerankerProtocol`,
  `QueryEmbedderProtocol` re-export) plus the typed
  `AccessPolicyFilter` projection, `RetrievalQuery`,
  `RetrievalCandidate` (with optional
  `document_projection`), `RankedCandidate`, and
  `RetrievalStageStats`.
- `src/domain/retrieval/rrf.py` is the pure RRF fusion
  function (deterministic tie-break, negative-K rejection).
- `src/application/retrieval/retrieve.py` is the
  orchestrator wiring the seven M8 stages: pre-filter
  projection (M0 pure function) -> embed (M7 capability) ->
  dense -> BM25 -> RRF fuse -> rerank (optional) ->
  post-rerank drop (M0 pure function). Typed errors
  (`EmptyRetrievalError`, `AccessDecisionUnavailableError`,
  `RetrievalDomainError`).
- `src/infrastructure/retrieval/` ships V1 in-memory
  adapters (cosine dense, BM25 with k1=1.5 / b=0.75,
  identity reranker stub). The typed `AccessPolicyFilter`
  projection is honored in the pre-scan predicate so the
  application decision cannot be circumvented.
- 15 new tests across
  `tests/domain/retrieval/test_rrf.py` (6),
  `tests/application/retrieval/test_retrieve_authorized_candidates.py`
  (6), and
  `tests/infrastructure/retrieval/test_in_memory_retrievers.py`
  (3).
- Combined pytest: 118 passed (was 101; +17 net of M7
  follow-up), 52 sandbox-skips, 0 failed. The M3/M5/M6
  API surface is unchanged at M8; no `/v1/*` endpoint
  lands here. M0 pure-function invocation count is now
  2 per retrieval call (pre-filter projection +
  post-rerank drop); citation verification lands at M9.
- Findings F-39 (algorithm parity with ParadeDB defaults),
  F-40 (candidate rebuild for projection observability)
  raised and accepted-Low.

---

## Next Task

**V1 implementation complete.** No new V1 milestones remaining. Future work is out-of-V1 and requires its own ADR per AGENTS.md.

A new agent reading this file should:

1. Verify the V1 release-ready state by running `python -m pytest`. Expected: **166 passed, 52 sandbox-skips, 0 failed**.
2. Read `docs/AUDITS/M14_REPORT.md` to confirm the release-gate closure evidence (launch contract boots DB-free, M9 pipeline envelope, M10 Regex Guard refusal flows through gate, M5..M11 stack smoke wires, M0 RBAC suite pass end-to-end through the M9 pipeline).
3. Read `MEMORY.md` for D-081..D-092 (V1 implementation cadence).
4. Read `docs/HANDOFF/DECISIONS_PENDING.md` for open questions D-001..D-006 (each owns its own out-of-V1 adoption milestone).
5. Optional: open the next-milestone-set discussion. Per AGENTS.md, any new milestone order or out-of-V1 work requires an ADR before touching code.


---

## Relevant Documents

Read these before starting M9:

- `ARCHITECTURE.md` — workflow orchestration, retrieval
  pipeline, prompt-protection ordering (Regex Guard ->
  RBAC Authorization -> Retrieval -> LLM Guard ->
  Generation, M10 introduces Regex Guard, M11 introduces
  LLM Guard).
- `DATABASE_SCHEMA.md` — retrieve `chunks.embedding` via
  `chunks_embedding_idx` HNSW (pgvector), `documents` via
  `documents_access_filter_idx`.
- `POLICIES.md` — the access decision is a single pure
  function invoked at every boundary. M9 introduces the
  citation-verification boundary.
- `WORKFLOWS.md` — the LangGraph state machine, node
  list, citation thread.
- `skills/project/architecture_review/SKILL.md` — review
  shape before adding nodes.
- `skills/project/retrieval_engine/SKILL.md` — pipeline
  shape, RRF K, access-decision enforcement points.
- `docs/AUDITS/M8_REPORT.md` — confirms M8 surface that
  M9 wires.

---

## Do Not Touch for M9

The M8 "Do Not Touch" carried-over list is now historical;

the M0..M7 prohibitions still apply. Additions for M9
prohibit pre-empting M10+:

- Do NOT pivot the M0 access-decision pure function. M9
  calls it unchanged at the citation-verification step
  (the third boundary per `AGENTS.md` Architectural
  Guardrails).
- Do NOT widen the M8 retrieval surface. The M8 typed
  `AccessPolicyFilter`, `RetrievalCandidate`,
  `DocumentProjection`, and `ranked` list are the input
  to M9; M9 reads from `workflow["retrieval"]` and does
  not re-implement the projection.
- Do NOT introduce streaming, SSE, or WebSocket -- V1
  stays request/response.
- Do NOT introduce CORS, OIDC, Okta, Entra ID, LDAP, or
  external IAM. The V1 auth path is JWT-only and unchanged
  from M5.
- Do NOT introduce multi-tenant concepts, ACL tables, or
  group/role authorization. These are out of V1 per
  AGENTS.md.
- Do NOT pin a specific generation, embedding, or reranker
  model in code. Generation lands at M9 as a
  capability-shaped port; the model capability is
  deferred to the owning adoption milestones (open
  questions D-002 / D-003).
- Do NOT touch the M3/M5/M6 API surface beyond adding the
  M9 `/v1/query` route. Existing routes (/health,
  /openapi.json, /docs, /redoc) and the JWT middleware
  behavior are unchanged.
- Do NOT introduce prompt-protection guards here. Regex
  Guard is M10; LLM Guard is M11. The primary request
  path at M9 invokes them in order but introduces only
  the nodes that wire the orchestrator.

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
 
