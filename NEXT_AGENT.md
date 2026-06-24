# NEXT_AGENT

This file is the operational entry point for a new agent. It answers
one question: "what is the next task, and what do I need to know to
do it?"

Read `AGENTS.md` first. Read `docs/HANDOFF/CURRENT_STATE.md` for a
snapshot of progress. Read the files listed under "Relevant
Documents" before doing anything.

---

## Current Milestone

**M6 — LangGraph Skeleton (actor-aware).**

## Current Status

**M0 closed on 2026-06-19 (commit `a78e21c`). M1 closed on
2026-06-19. M2 closed on `main` at `7849d89`. M3 closed at
`fb110bd`. M4 closed at `03351c4`. All pushed to `origin/main`.
M5 is closed (this turn) on `rag-langgraph`; the next advisory
step reviews fast-forward against `main` once verification is
recorded. M6 (LangGraph Skeleton, actor-aware) is the next
implementation milestone.**

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

M5 silhouette (this turn; closure record at
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

---

## Next Task

The current task is to land **M5 — JWT Validation** on
`main`:

- HS256-only signer, no JWKS (D-001). M5 introduces a real
  signing/verification boundary; pick RS256 or JWKS later.
- Introduce `src/application/auth/` as a dedicated
  application package (D-038). The auth package owns the
  `VerifyJwtToken` use case and the typed-actor projection.
- Add a FastAPI middleware at the API boundary that calls the
  `VerifyJwtToken` use case on every request (D-039). Bad or
  missing tokens produce 401 and a `code=JWT_INVALID` row in
  `audit_logs` (route through M4's `RecordAuditEvent`).
- `__main__.py` is updated to construct the pool and pass it
  to the now-real run-time FastAPI factory.
- `create_app(audit_repo=None)` keeps accepting the seam; M5
  additionally accepts `jwt_signer` so token verification is
  configurable.

### How to test (M5 prelude)

- `.venv\Scripts\python.exe -m pytest -q tests/api tests/rbac
  tests/infrastructure tests/application` is green.
- `grep -rE "fastapi|pydantic|uvicorn" src/domain/` returns
  zero rows.
- `grep -rE "asyncpg|psycopg|sqlalchemy" src/application/
  src/domain/` returns zero rows (the auth package must
  import only from ports, not from any DB driver).

### How to verify before moving on to M6

- The M4 closure record at `docs/AUDITS/M4_REPORT.md` remains
  accurate.
- The M5 closure record at `docs/AUDITS/M5_REPORT.md` carries
  the route + audit-row + JWT-validator behavior, including
  a typed failure-row that lands through M4's
  `RecordAuditEvent`.
- The launch contract `uvicorn src.api.app:create_app
  --factory` boots an instance with `/health` returning 200
  *without* a DB only when `audit_repo=None` and a dev signing
  secret is provided. A DB-backed audit row lands for bad
  tokens when a pool is supplied.

---

## Relevant Documents

Read these before starting M5:

- `ARCHITECTURE.md` — JWT validation is the first boundary on
  the primary request path; the workflow state shape is
  `{user_id, department, clearance, role, correlation_id}`.
- `DATABASE_SCHEMA.md` — V1 tables, including `users` (with
  `external_subject`) and `audit_logs`.
- `POLICIES.md` — JWT requirements, required claims
  (`subject`, `department`, `clearance`, `expiration`), and
  audit row on every authentication outcome with
  `reason_code = JWT_INVALID`.
- `WORKFLOWS.md` — JWT validation is the first step in the
  query-and-answer flow; bad tokens return 401 with no
  generation.
- `skills/project/database_design/SKILL.md` — schema and
  constraint invariants for the `users` table.
- `docs/AUDITS/M4_REPORT.md` — confirms the M4 audit intake
  is the seam M5 invokes to record token failures.

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
 
