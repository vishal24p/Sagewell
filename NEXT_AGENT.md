# NEXT_AGENT

This file is the operational entry point for a new agent. It answers
one question: "what is the next task, and what do I need to know to
do it?"

Read `AGENTS.md` first. Read `docs/HANDOFF/CURRENT_STATE.md` for a
snapshot of progress. Read the files listed under "Relevant
Documents" before doing anything.

---

## Current Milestone

**M7 — Ingestion (LlamaIndex idempotent re-ingestion).**

## Current Status

**M0 closed on 2026-06-19 (commit `a78e21c`). M1 closed on
2026-06-19. M2 closed on `main` at `7849d89`. M3 closed at
`fb110bd`. M4 closed at `03351c4`. All pushed to `origin/main`.
M5 is closed on `feat/m5-jwt-validation` (this repo's remote).
M6 is closed on `feat/m6-langgraph-skeleton` (also this repo's
remote). M7 (Ingestion) is the next implementation milestone.**

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
- Combined pytest: **86 passed** (was 73 at M5; net +13 from
  M6), 52 sandbox-skips, 0 failed.
- 8 distinct tests at `tests/application/workflow/test_workflow_state.py`
  + 5 at `tests/infrastructure/langgraph/test_workflow.py`.
- The M3/M5 API surface is unchanged at M6: no `/v1/*`
  endpoint. The D-028 forward-hook surface
  (workflow → api, never api → workflow) is preserved.
- Finding F-35 (channel-shape vs typed-state split) raised,
  accepted-Low, and documented in `docs/AUDITS/M6_REPORT.md`.

---

## Next Task

The current task is to land **M7 — Ingestion** on a feature
branch:

- LlamaIndex loads documents from the connector surface,
  semantic-chunks, and embeds through a capability-based
  embedding port (the model ID is owned by settings; no
  module pins a specific provider / version).
- Idempotent on `documents.content_checksum`: the same
  checksum re-applied leaves the `documents` row count
  unchanged (no duplicate insert; replaced chunks are not
  readable from the search path until the success audit
  log is written).
- Replaced chunks are not searchable. The chunk row is
  marked `replaced_by` so the search path can exclude it.
- The job outcome (success / failure / partial) is written
  to `audit_logs` through the M4 `RecordAuditEvent` use
  case.
- Ingestion is exercised in-process; no background worker
  is introduced at M7.

### How to test (M7 prelude)

- `.venv\Scripts\python.exe -m pytest -q tests/api tests/rbac
  tests/infrastructure tests/application` is green.
- `grep -rE "fastapi|pydantic|uvicorn" src/domain/` returns
  zero rows.
- `grep -rE "asyncpg|psycopg|sqlalchemy" src/application/
  src/domain/` returns zero rows (the new ingestion ports /
  use case must import only from `src/domain/ports/`, not
  from any DB driver).

### How to verify before moving on to M8

- The M5/M6 closure records at `docs/AUDITS/M5_REPORT.md`
  and `docs/AUDITS/M6_REPORT.md` remain accurate.
- The M7 closure record at `docs/AUDITS/M7_REPORT.md`
  carries the idempotence-on-content-checksum evidence,
  the replaced-chunks are not searchable evidence, and the
  job-outcome audit row evidence.
- The launch contract `uvicorn src.api.app:create_app
  --factory` boots an instance with `/health` returning 200
  *without* a DB only when `audit_repo=None` and a dev signing
  secret is provided. M7 does NOT change the launch
  contract.
- The combined pytest stays green; the M7 tests add at least
  one test per guarantee above.

---

## Relevant Documents

Read these before starting M7:

- `ARCHITECTURE.md` — LlamaIndex is the document-loading,
  semantic-chunking, ingestion, and retrieval-abstraction
  boundary. LangGraph owns workflow orchestration.
- `DATABASE_SCHEMA.md` — V1 tables: `documents` (with
  `content_checksum`), `chunks`, `audit_logs`,
  `retrieval_logs`, `evaluation_results`, `users`. The
  ingestion ports must respect the V1 schema.
- `POLICIES.md` — Ingestion writes are auditable; an
  audit row is required for every job outcome.
- `WORKFLOWS.md` — Ingestion runs outside the request path;
  it is a background job with a typed outcome.
- `skills/project/ingestion_pipeline/SKILL.md` — project skill
  on connector / chunker / embedding boundaries, idempotence,
  replaced-chunk semantics.
- `skills/project/database_design/SKILL.md` — schema and
  constraint invariants for `documents` and `chunks`.
- `docs/AUDITS/M5_REPORT.md` — confirms the JWT / actor
  projection seam that the search path uses to filter
  candidates; M7 does not change this seam.
- `docs/AUDITS/M6_REPORT.md` — confirms the typed
  `WorkflowState` boundary; M7 ingestion runs through the
  same state machine but is invoked from a background job,
  not a `/v1/*` route.

---

## Do Not Touch for M7

The M0..M6 "Do Not Touch" lists still apply. Additions for
M7 are NOT prohibitions against working on M7; they are
prohibitions against pre-empting M8+ while working on M7:

- Do NOT introduce a background worker, a queue, or a
  scheduler. M7 ingestion runs in-process; the only
  side-effect is the database writes.
- Do NOT alter the M0 IMM reason-code set. M7 introduces
  ingestion reason codes (`ingestion_succeeded` /
  `ingestion_failed` / `ingestion_partial`) through the M4
  audit-intake; these are caller-supplied reason_codes and
  do not change the M0 seven IMM codes.
- Do NOT introduce a `/v1/*` endpoint that proxies to
  ingestion. Ingestion is not request-time surface at M7.
- Do NOT pivot the access-decision function. M7 has no
  authorization boundary; ingestion writes documents
  by content_checksum regardless of actor. The actor is
  associated with the audit row, not the access decision.
- Do NOT introduce a vector index hint or a pgvector
  configuration knob. The vector store lands at M8.
- Do NOT introduce streaming, SSE, or WebSocket — V1
  stays request/response.
- Do NOT introduce CORS, OIDC, Okta, Entra ID, LDAP, or
  external IAM. The V1 auth path is JWT-only and unchanged
  from M5.
- Do NOT introduce multi-tenant concepts, ACL tables, or
  group/role authorization. These are out of V1 per
  AGENTS.md.

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
 
