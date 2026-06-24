# Current State

**Last updated**: 2026-06-21

This file is a snapshot of repository progress. It is operational,
not authoritative. For architecture, see `ARCHITECTURE.md`. For the
implementation roadmap, see `PROJECT_STATUS.md`. For pending
decisions, see `docs/HANDOFF/DECISIONS_PENDING.md`. For unresolved
engineering concerns, see `docs/HANDOFF/KNOWN_ISSUES.md`.

---

## Current Architecture Version

Architecture version: **V1**.

Source of truth: `docs/adr/0001-single-tenant-enterprise-rag-baseline.md`.

Key invariants of V1:

- Single-company, single-tenant Enterprise RAG.
- Authorization: department + clearance only.
- Retrieval: dense + BM25 + RRF + cross-encoder reranking.
- Workflow orchestration: LangGraph.
- Document loading, semantic chunking, ingestion, retrieval
  abstractions: LlamaIndex.
- Data store: PostgreSQL with `pgvector` and `pg_search`.
- Authentication: JWT.
- Prompt protection: regex guard and LLM guard on the primary
  request path. Regex Guard runs before RBAC and retrieval.
- Evaluation: RAGAS and the RBAC Access Outcome Suite (both
  required).
- Models: capability-based.
- V1 tables: `users`, `documents`, `chunks`, `audit_logs`,
  `retrieval_logs`, `evaluation_results`.

---

## Current Milestone

**M0..M6 closed. M7 (Ingestion) is the next milestone.**

M1 closed on 2026-06-19 after developer-side verification ran
clean against the remediated code (F-21 image tag, F-22 healthcheck
escaping, F-23 host port). M2 implementation committed on the
2026-06-20 developer-side Postgres parity run: ports layer at
`src/domain/ports/`, in-memory and Postgres adapters under
`src/infrastructure/repositories/`, parity tests at
`tests/infrastructure/repositories/`. The M0 RBAC Access Outcome
Suite still 31/31 green; combined pytest reports 81 passed and
2 by-design skips. Findings F-24..F-28 surfaced during the
parity run and were fixed before closure.

M5 closed on 2026-06-21. Closure report at
`docs/AUDITS/M5_REPORT.md`. Combined pytest 73 passed, 52
sandbox-skips, 0 failed. M0 RBAC still 31/31; M3 tests/api still
13/13; M4 application tests still 10/10; M5 tests/application/auth
10/10. Findings F-31..F-34 surfaced during verification and were
resolved in this session.

M6 closed on 2026-06-21. Closure report at
`docs/AUDITS/M6_REPORT.md`. Combined pytest 86 passed, 52
sandbox-skips, 0 failed (net +13 tests from M5). M0 RBAC still
31/31; M3 tests/api still 13/13; M4 tests/application/audit_event
still 10/10; M5 tests/application/auth still 10/10. The M3/M5 API
route surface is unchanged at M6; no `/v1/*` endpoint lands at M6.
F-35 (channel-shape vs typed-state split, accepted-Low) raised
during verification and documented in the closure report.

**Current branch**: `feat/m6-langgraph-skeleton` (M6 commit will
land here; `main` and `feat/m5-jwt-validation` are untouched).

M3 implementation is complete and committed on 2026-06-20 at
`fb110bd` (pushed to `origin/main`). The route surface is
exactly `GET /health`, `GET /openapi.json`, `GET /docs`,
`GET /redoc`. The launch contract is
`uvicorn src.api.app:create_app --factory`. The M3 package is
a pure API skeleton, no DB, no JWT, no query-answer path, and
no audit/correlation router. At M5, `/openapi.json` becomes
JWT-protected while `/health`, `/docs`, and `/redoc` continue
to skip the auth middleware (D-039, D-040 Q3).

M4 implementation is complete and committed on 2026-06-20 at
`03351c4` (pushed to `origin/main`). M4 introduces the
application layer's audit intake use case under
`src/application/audit_event/`. M4 ships the use case only —
no middleware, no test endpoint, and no automatic request-time
audit writes; the launch contract stays DB-free until M5.
Findings F-29 and F-30 from M3 are recorded in
`docs/AUDITS/FINDINGS.md` and reflected in upstream docs.
Closure record at `docs/AUDITS/M4_REPORT.md`.

Source of truth: `PROJECT_STATUS.md` M0-M14.

---

## Completed

| Milestone | Description | Date |
|---|---|---|
| M0 | Access Decision (pure) and RBAC Access Outcome Suite. | 2026-06-19 |
| M1 | Schema, Migrations, Fixtures, Indexes. Verified via the F-21 (image tag), F-22 (healthcheck escaping), and F-23 (host port) remedies. | 2026-06-19 |
| M2 | Repositories (ports + in-memory + Postgres adapters + parity tests). Developer-side Postgres parity verified on `localhost:55432`. F-24..F-28 surfaced and resolved during the parity run. | 2026-06-20 |
| M3 | API Skeleton (reduced scope). Route surface is exactly `/health`, `/openapi.json`, `/docs`, `/redoc`; launch contract `uvicorn src.api.app:create_app --factory`. Closure commit `fb110bd` on `main`. | 2026-06-20 |
| M4 | Audit Infrastructure (application use case only). `src/application/audit_event/RecordAuditEvent` use case; 10 distinct passing tests; launch contract stays DB-free until M5. Closure commit `03351c4` on `main`. | 2026-06-20 |
| M5 | JWT Validation. `src/application/auth/` (VerifyJwtToken + HS256 signer + typed-actor projection); `src/api/middleware/auth.py` pure-ASGI JWT middleware; `create_app(jwt_signer=...)` DI seam; `__main__` reads `SAGEWELL_JWT_SECRET`. Bad tokens return 401 and a `reason_code=jwt_invalid` audit row through M4's `RecordAuditEvent`. `/health`, `/docs`, `/redoc` skip the middleware; `/openapi.json` is JWT-protected. Combined pytest 73 passed, 52 sandbox-skips, 0 failed. Closure report at `docs/AUDITS/M5_REPORT.md`; findings F-31..F-34 surfaced and resolved during verification. | 2026-06-21 |
| M6 | LangGraph Skeleton (actor-aware). `src/application/workflow/` ships the frozen `WorkflowState` dataclass (required: `user_id`, `department`, `clearance`, `role`, `correlation_id`; optional: `query`) with the `from_actor` typed factory and `__post_init__` fail-closed invariant. Typed-error hierarchy (`WorkflowDomainError` -> `AnonymousExecutionError` -> `IncompleteActorError`) at `src/application/workflow/errors.py`. `src/infrastructure/langgraph/workflow.py` binds the typed state to a LangGraph channel (`_WorkflowChannel` TypedDict with `total=False`) and ships the empty skeleton graph (`START -> noop_node -> END`) plus the async `run_workflow(state)` application entrypoint. Combined pytest 86 passed, 52 sandbox-skips, 0 failed. The M3/M5 API route surface is unchanged at M6; no `/v1/*` endpoint lands at M6. Closure report at `docs/AUDITS/M6_REPORT.md`; finding F-35 (channel-shape vs typed-state split, accepted-Low) documented. | 2026-06-21 |

### Completed In Documentation

| Item | Date |
|---|---|
| V1 architecture approved (`docs/adr/0001-...`) | 2026-06-19 |
| Documentation audit and corrections (`docs/AUDIT_REPORT.md`) | 2026-06-19 |
| Architecture verification pass (`docs/VERIFICATION_REPORT.md`) | 2026-06-19 |
| Implementation roadmap published (`PROJECT_STATUS.md` M0-M14) | 2026-06-19 |
| Roadmap refinement: JWT before LangGraph skeleton | 2026-06-19 |
| Agent-handoff refactor: `AGENTS.md` reduced to constitution, `NEXT_AGENT.md` and `docs/HANDOFF/` created | 2026-06-19 |

---

## In Progress

| Milestone | Description | Owner | Started |
|---|---|---|---|
| (none) | M0..M6 closed; M7 (Ingestion) is up next on a new feature branch (`feat/m7-ingestion` once staged). | (none assigned) | (not started) |

---

## Recently Completed

| Date | Item |
|---|---|
| 2026-06-19 | M0 — Access Decision (pure) implemented as `src/domain/access/` with `Clearance` enum, `User`/`Document` value types, and `decide(user, document) -> (allowed, reason)`. RBAC Access Outcome Suite placed at `tests/rbac/test_access_decision.py` (31/31 passing). Function is pure: no framework imports, no database calls. Missing authorization inputs fail closed with explicit reason codes. Role-regression test confirms `users.role` does not influence the decision. |
| 2026-06-19 | M1 — Schema, Migrations, Fixtures, Indexes authored (unverified from the sandbox). Docker compose at `docker/compose.dev.yml` brings up Postgres + ParadeDB `pg_search`. Migrations `001_extensions`, `002_schema`, `003_indexes`, `004_fixtures` are reversible SQL pairs under `migrations/`. Fixtures are SQL under `db/fixtures/` and use a `fixture-` prefix and `source_system='fixture'` so rollback does not touch real data. Apply and rollback run via `infrastructure/migrations/{apply,rollback}.sh`. ADRs `0002-pg-search-paradedb.md` and `0003-raw-sql-migrations.md` capture the M1 decisions. Verification requires a Postgres reachable from a developer environment; the sandbox does not run Docker. |
| 2026-06-20 | M2 — Repositories (ports + in-memory + Postgres adapters + parity tests) implemented and developer-side verified on `localhost:55432`. RBAC Access Outcome Suite remains 31/31 green. Combined pytest: 81 passed, 2 by-design skips, 0 failed, 0 errors. Findings F-24..F-28 surfaced and resolved during the parity run. M2 status flips from `Implemented, Verified Ready` to `Closed`. |
| 2026-06-20 | M3 — API Skeleton (reduced scope) implemented and committed at `fb110bd` on `main` (pushed to `origin/main`). `src/api/app.py` exports `create_app()` factory; routes are exactly `/health`, `/openapi.json`, `/docs`, `/redoc`. Launch contract: `uvicorn src.api.app:create_app --factory`. No DB, no JWT, no query-answer stub. The catch-all error middleware logs `correlation_id`, `exception_type`, and `exc_message` (the third key is deliberately spelled `exc_message` to avoid colliding with the std-lib `LogRecord` reserved `message` field). `tests/api/` lands 13 distinct passing tests. Combined pytest: 44 passed across `tests/api`+`tests/rbac` and 52 sandbox-skips total from the Postgres dev-compose tests; M0 RBAC suite still 31/31 green. F-29 and F-30 surfaced and resolved during the M3 implementation. Closure record at `docs/AUDITS/M3_REPORT.md`. |
| 2026-06-20 | M4 — Audit Infrastructure (application use case only) implemented and committed at `03351c4` on `main` (pushed to `origin/main`). `src/application/audit_event/record.py` ships the `RecordAuditEvent` use case with a `Clock` Protocol, `RecordAuditCommand` DTO, `AuditEventId` newtype, and `AuditEventError` / `PersistenceFailure(AuditEventError)`. `src/api/app.py` accepts an optional `audit_repo` parameter (no `pool` parameter, no asyncpg import). D-029..D-037 locked: M4 ships no middleware, no test endpoint, no automatic request-time audit writes; `__main__.py` continues to launch DB-free. `tests/application/audit_event/` lands 10 distinct passing tests. Combined pytest: 54 passed, 52 sandbox-skips, 0 failed; M0 RBAC still 31/31, M3 tests/api still 13/13. Closure record at `docs/AUDITS/M4_REPORT.md`. |
| 2026-06-21 | M5 — JWT Validation implemented on `rag-langgraph`. `src/application/auth/` ships the `VerifyJwtToken` use case with a `Clock` Protocol, `VerifyJwtTokenCommand` DTO, typed-failure hierarchy (`AuthFailure` + `JwtMissing`/`JwtMalformed`/`JwtBadSignature`/`JwtExpired`/`JwtInvalid`), `AuthActor` projection, `HS256JwtSigner` implementing the `JwtSigner` Protocol (PyJWT 2.x + manual `exp`-against-clock), and the `UNKNOWN_USER_ACTOR` typed failure carrier. `src/api/middleware/auth.py` is a pure-ASGI JWT middleware that runs `VerifyJwtToken` on every request, skips `{"/health", "/docs", "/redoc"}`, and translates failures to the canonical `{code, message, correlation_id}` 401 envelope. `create_app(jwt_signer=...)` mounts the auth middleware; `__main__` reads `SAGEWELL_JWT_SECRET` and constructs `HS256JwtSigner`. Reason-code whitelist at `src/domain/ports/reason_codes.py` widens to include `jwt_invalid` (the `ReasonCode` Literal stays narrowed to the seven M0 codes so the access-decision output shape is preserved). Combined pytest 73 passed, 52 sandbox-skips, 0 failed. M0 RBAC still 31/31, M3 tests/api still 13/13, M4 application tests still 10/10. F-31 (NameError on `verify_jwt` from middleware dispatchers), F-32 (FastAPI 422 from unannounced `request` parameter), F-33 (PyJWT InsecureKeyLengthWarning on sub-32-byte secrets), and F-34 (state lookup via `scope["app"]` rather than `self._app`) all surfaced and were resolved this session. Closure record at `docs/AUDITS/M5_REPORT.md`. |
| 2026-06-21 | M6 — LangGraph Skeleton (actor-aware) implemented on `feat/m6-langgraph-skeleton`. `src/application/workflow/` package ships the frozen `WorkflowState` dataclass with required `{user_id, department, clearance, role, correlation_id}` and optional `query`, plus the `from_actor` typed factory and `__post_init__` fail-closed invariant. Typed-error hierarchy (`WorkflowDomainError` -> `AnonymousExecutionError` -> `IncompleteActorError`) at `src/application/workflow/errors.py`. `src/infrastructure/langgraph/workflow.py` is the only place that imports `langgraph`; it ships `build_initial_channel`, `from_state_dict`, `to_state_dict`, `build_skeleton_graph` (empty `START -> noop_node -> END`), and the async `run_workflow(state)` application entrypoint. Dependency: `langgraph>=0.4,<0.6` added to `pyproject.toml`. 13 new tests across `tests/application/workflow/` (8) and `tests/infrastructure/langgraph/` (5). Combined pytest 86 passed (was 73; +13), 52 sandbox-skips, 0 failed. The M3/M5 API route surface is unchanged at M6; no `/v1/*` endpoint lands here. D-028 forward-hook rule preserved (workflow -> api, never api -> workflow). F-35 (channel-shape vs typed-state split, accepted-Low) documented in the closure report. Closure record at `docs/AUDITS/M6_REPORT.md`. |

---

## Not Started

| Milestone | Description |
|---|---|
| M7 | Ingestion. |
| M8 | Retrieval with Access Filter. |
| M9 | Workflow Wiring with Citations. |
| M10 | Regex Guard. |
| M11 | LLM Guard. |
| M12 | Audit and Retrieval Logs (complete). |
| M13 | RAGAS Evaluation. |
| M14 | End-to-end Hardening. |

---

## Recently Decided

| Date | Decision |
|---|---|
| 2026-06-19 | V1 architecture baseline accepted. |
| 2026-06-19 | `MEMORY.md` is the authoritative decisions log. `context/decisions.md` is a pointer. |
| 2026-06-19 | Local skills are the source of routing. `skills/project/` for project skills, `skills/external/` for vendored external skills. |
| 2026-06-19 | Project name is Sagewell. Intended GitHub repository name is `sagewell`. |
| 2026-06-19 | V1 implementation sequencing: JWT before LangGraph skeleton. Workflow state typed with `user_id`, `department`, `clearance`, `role`, `correlation_id` from the first test. |
| 2026-06-19 | Agent-handoff architecture: `AGENTS.md` is the constitution. `NEXT_AGENT.md` carries operational state. `docs/HANDOFF/` carries progress, pending decisions, and known issues. |
| 2026-06-19 | M0 Access Decision landed as a pure function under `src/domain/access/`, with the RBAC Access Outcome Suite under `tests/rbac/` (31/31 passing). |
| 2026-06-19 | V1 lexical search uses ParadeDB `pg_search`. Schema migration creates the extension; version pinning is deferred to deployment. |
| 2026-06-19 | Migrations are raw numbered SQL pairs. Run tooling is `infrastructure/migrations/{apply,rollback}.sh`. No Alembic, SQLAlchemy, `dbmate`, `yoyo-migrations`, or `sqitch`. |
| 2026-06-19 | M1 FK behavior is RESTRICT on every cross-table reference. Soft-delete goes through the `status` column. |
| 2026-06-19 | `audit_logs.reason_code` is TEXT with no DB-level constraint; only the M0 imm codes are emitted in M1. |
| 2026-06-19 | `chunks.embedding` is fixed at `vector(1536)`. The dimension is a column-level constraint; any change requires ADR-0004-style review. |
| 2026-06-19 | `users.external_subject` and `users.email` are UNIQUE. The former is the JWT look-up key for M5. |
| 2026-06-19 | `users.updated_at` and `documents.updated_at` are kept current by `BEFORE UPDATE` triggers via the `sagewell_touch_updated_at` function. |
| 2026-06-19 | Migration runner is portable. `apply.sh` passes `:fixtures_dir` to `psql -v`; `rollback.sh` refuses to run without `SAGEWELL_ROLLBACK_CONFIRM=I_UNDERSTAND`. |
| 2026-06-19 | Engineering findings recorded in `docs/AUDITS/FINDINGS.md`; remediation report at `docs/AUDITS/M1_REMEDIATION_REPORT.md`; verification package at `docs/AUDITS/M1_VERIFICATION_REPORT.md` (status PENDING LOCAL EXECUTION). |
| 2026-06-19 | Dev compose image tag corrected: `paradedb/paradedb:pg17`. Investigation report `docs/AUDITS/INVESTIGATION_REPORT_M1_IMAGE.md`; finding F-21 closed; ADR-0002 paragraph amended in place. Production deployments pin by digest. |
| 2026-06-19 | Dev compose healthcheck re-routed through `echo ... \| psql -tAX \| grep -q '^1$'` to dodge the YAML single-quote vs SQL single-quote collision. Finding F-22 closed; no schema, migration, or ADR changes required. |
| 2026-06-19 | Dev compose host port remapped from 5432 to 55432 to avoid a host-resident Postgres collision. Diagnostic findings F-23 recorded; apply.sh unchanged; developer sets `SAGEWELL_DB_URL` to `localhost:55432`. |
| 2026-06-19 | M1 closed. Engineering findings F-21 (image tag), F-22 (healthcheck quoting), and F-23 (host port) recorded as resolved; `docs/AUDITS/M1_VERIFICATION_REPORT.md` reaches PASSED; m1 verification report and remediation report closed. M2 begins after the user confirms the M2 pre-implementation questions. |
| 2026-06-20 | M2 ports layer at `src/domain/ports/`. Value objects plus Protocols for `User`, `Document`, `Chunk`, `AuditEvent`, `RetrievalLog`, `EvaluationResult`. The M0 RBAC suite imports from ports; no shim. |
| 2026-06-20 | M2 driver stack: `asyncpg>=0.30,<0.32`, `pgvector>=0.3,<0.5`, `pytest-asyncio>=0.23,<2.0`. pgvector codec via `pgvector.asyncpg.register_vector` (NOT a package named `asyncpg-pgvector`; that name is not on PyPI). JSONB codec also registered. |
| 2026-06-20 | M2 test isolation: per-test `TRUNCATE ... RESTART IDENTITY CASCADE` in `clean_postgres_state` fixture. Postgres tests skip when `SAGEWELL_DB_URL` is unset/unreachable. After the F-25 / F-24 fixes, `postgres_pool` is function-scoped to bind cleanly to the per-test event loop, and `seed_parent_rows` covers the FK parent gap. |
| 2026-06-20 | M2 SQL-level filters never combine department + clearance. Status/id/source only. The compound decision remains the access-decision pure function's responsibility. |
| 2026-06-20 | EvaluationResultRepository validators (`in_memory/evaluation_results.py`, `postgres/evaluation_results.py`) hardened after F-28 surfaced a `TypeError` from `raw_string not in EnumType`. Both now check `isinstance(result.suite, Suite) and result.suite.value in {member.value for member in Suite}` and raise `PersistenceError` uniformly. |
| 2026-06-20 | M2 closed. Developer-side parity run on `localhost:55432` reported 50/52 repository tests passed (2 by-design skips, 0 failed, 0 errors), and combined pytest 81 passed / 2 skipped. M3 (API Skeleton) is the next milestone. (Superseded 2026-06-20: M3 closed at `fb110bd`. M4 — Audit Infrastructure — is the next milestone.) |
| 2026-06-20 | AuditLogRepository enforces the seven M0 IMM reason codes at append time. Other strings rejected with `PersistenceError`. |
| 2026-06-20 | M3 reduced-scope decision: pure API skeleton. Dropped JWT stub, query-answer stub, correlation-router reads, DB dependency. M3's route surface = `GET /health`, `GET /openapi.json`, `GET /docs`, `GET /redoc`. Launch contract: `uvicorn src.api.app:create_app --factory`. |
| 2026-06-20 | D-020 locked: UUID4 for correlation ids. |
| 2026-06-20 | D-021 locked: error envelope `{code, message, correlation_id}` minimum. |
| 2026-06-20 | D-024 locked: settings = `SAGEWELL_LOG_LEVEL`, `SAGEWELL_API_HOST`, `SAGEWELL_API_PORT` only. `SAGEWELL_CORS_ALLOWED_ORIGINS` removed from M3. |
| 2026-06-20 | D-025 locked: `/docs`, `/redoc`, `/openapi.json` enabled by default. |
| 2026-06-20 | D-026 locked: keep `src/api/__main__.py`. |
| 2026-06-20 | D-027 locked: catch-all log keys = `correlation_id`, `exception_type`, `exc_message`. The third key is renamed from the originally-spoken `message` because the std-lib `LogRecord` reserves `message`; renaming to `exc_message` keeps the three D-027 keys readable while satisfying logbook invariants. |
| 2026-06-20 | M4 reduced-scope decision: M4 ships the application audit-intake use case only. No middleware, no test endpoint, no automatic request-time audit writes. M4 does NOT widen the seven-code M0 IMM reason-code whitelist; I-001 stays open. |
| 2026-06-20 | D-029 locked: M4 ships the application use case only. |
| 2026-06-20 | D-030 locked: `src/domain/ports/reason_codes.py` is unchanged at M4. |
| 2026-06-20 | D-031 locked: `create_app(*, audit_repo=None)` DI seam. `__main__.py` owns pool construction. |
| 2026-06-20 | D-032 locked: no automatic audit writes during requests at M4. The launch contract stays DB-free until M5. |
| 2026-06-20 | D-033 locked: `AUDIT_HISTORY.md` row 16 is edited (not split). |
| 2026-06-20 | D-034 locked: `src/api/__init__.py` docstring is unchanged at M4. |
| 2026-06-20 | D-035 locked: `create_app` keeps `audit_repo` only; no `pool` parameter, no `TYPE_CHECKING` asyncpg. |
| 2026-06-20 | D-036 locked: two-error split kept — `AuditEventError` and `PersistenceFailure(AuditEventError)`. |
| 2026-06-20 | D-037 locked: M4 implementation sign-off. |
| 2026-06-21 | D-001 implementation carve-out: HS256 + shared secret from `SAGEWELL_JWT_SECRET` at M5. Long-term question is open in `docs/HANDOFF/DECISIONS_PENDING.md` `## Open` section (RS256 + JWKS or external KMS). |
| 2026-06-21 | D-038 locked: M5 ships a dedicated `src/application/auth/` package. Sibling to `src/application/audit_event/`. Owns `VerifyJwtToken`, the typed-actor projection (`AuthActor`), the typed-failure hierarchy (`AuthFailure` subclasses), and the `HS256JwtSigner`. Imports only from `src/domain/ports/` and intra-application. |
| 2026-06-21 | D-039 locked: M5 adds `src/api/middleware/auth.py`, a pure-ASGI JWT validation middleware. Matches the M3 `CorrelationIdMiddleware` style. Calls `VerifyJwtToken` on every request that is not in `PUBLIC_PATHS = {"/health", "/docs", "/redoc"}`. Bad/missing tokens return 401 with the canonical `{code: "auth_failed", message, correlation_id}` envelope and a `RecordAuditEvent` row carrying `reason_code = "jwt_invalid"` and `metadata["auth_failure_carrier"] = "unknown-user"`. |
| 2026-06-21 | D-040 Q1: Trust the JWT after successful verification; no DB lookup in auth path. Q2: Failure rows use the typed `UNKNOWN_USER_ACTOR` carrier (`user_id="unknown-user"`, `department="unknown"`, `clearance="unknown"`, `role="unknown"`); the actual `actor_user_id: Optional[int]` None is preserved end-to-end on `audit_logs.actor_user_id`. Q3: `/openapi.json` is JWT-protected when the middleware is wired; only `/health`, `/docs`, `/redoc` skip. |
| 2026-06-21 | D-041 / D-042 (this milestone): middleware classes are pure-ASGI (`__call__(scope, receive, send)`); the runtime lookups for `app.state.verify_jwt` go through `scope.get("app")` rather than `self._app`. `self._app` is the inner wrapped application, not the FastAPI host, so a `state` read through `self._app.state` would resolve through the wrong layer. The FastAPI host is injected by Starlette into `scope["app"]`. |
| 2026-06-21 | D-043 (this milestone): `src/application/auth/**` import-graph invariants. Verified by AST scan: zero `fastapi`, `pydantic`, `uvicorn`, `asyncpg`, `psycopg`, `sqlalchemy` import-statements in `src/application/` or `src/domain/`. Docstrings may mention "no asyncpg" without violating the constraint. |
| 2026-06-21 | D-044 (this milestone): reason-code widening lives in `is_allowed_reason_code()`, NOT in the `ReasonCode` Literal. The literal bounds the access-decision's output type and stays narrowed to the seven M0 codes; `_ALLOWED_REASON_CODES: frozenset[str]` accumulates the V1 application's full set across milestones. New V1 codes extend the predicate, not the literal. |
| 2026-06-21 | `src/api/__init__.py` launcher hook: `__main__.py` reads `Settings.jwt_secret` (bytes) and constructs an `HS256JwtSigner` only when set. When unset, the launch contract stays DB-free and auth-less (M3 invariant preserved). `SAGEWELL_DB_URL` is not consumed at M5; M5 keeps the launch DB-free unless a future milestone carves out explicit pool construction. |
| 2026-06-21 | `src/api/middleware/auth.py` wires successful verification to `scope["state"]["actor"] = AuthActor`. M6+ consumers (LangGraph state machine) read this projection directly into their typed `{user_id, department, clearance, role, correlation_id}` state. |
| 2026-06-21 | M5 closed on `rag-langgraph` (not yet pushed to `main`). Findings F-31 (NameError), F-32 (FastAPI 422 from unannounced `request` parameter), F-33 (PyJWT InsecureKeyLengthWarning on sub-32-byte secrets), and F-34 (state lookup via `scope["app"]` rather than `self._app`) all surfaced during initial verification and were resolved this session. Closure report at `docs/AUDITS/M5_REPORT.md`. |
| 2026-06-21 | D-045 locked: M6 ships `src/application/workflow/` as a third application-package sibling to `audit_event/` and `auth/`. The package owns the typed-state dataclass and the typed-failure hierarchy (`WorkflowDomainError` -> `AnonymousExecutionError` -> `IncompleteActorError`). Imports only standard library + intra-application + domain ports. |
| 2026-06-21 | D-046 locked: M6 introduces `src/infrastructure/langgraph/` as the framework-adapter layer. The adapter binds the typed application state to a LangGraph `StateGraph` channel via `build_initial_channel` / `from_state_dict` helpers. It is the only place in the project that imports `langgraph`. |
| 2026-06-21 | D-047 locked: M6 ships a frozen `WorkflowState` dataclass with required `{user_id, department, clearance, role, correlation_id}` plus an optional `query`. Construction via the typed factory `WorkflowState.from_actor(actor)` is the canonical entry; the `__post_init__` invariant refuses non-blank required fields, providing defense in depth against direct-constructor misuse. |
| 2026-06-21 | D-048 locked: M6's `run_workflow(state)` is the canonical async application entrypoint. It rejects non-`WorkflowState` input with `IncompleteActorError`. The skeleton graph is `START -> noop_node -> END`; the noop is identity. Future M7-M9 milestones replace `noop_node` with retrieval-and-rerank-and-generation nodes. |
| 2026-06-21 | D-049 locked: the workflow package MUST NOT import `src/api/`, `src/infrastructure/`, `fastapi`, `pydantic`, `uvicorn`, `asyncpg`, `psycopg`, `sqlalchemy`, or any framework SDK. The framework adapter under `src/infrastructure/langgraph/` binds the typed state to LangGraph; the application package stays framework-free. Verified by an AST-based import-statement scan. |
| 2026-06-21 | D-050 locked: the M3/M5 route surface is unchanged at M6. `/health`, `/openapi.json`, `/docs`, `/redoc` continue to be the API boundary. M6 deliberately does NOT mount a `/v1/*` endpoint; the `/v1/*` endpoint lands at the milestone that wires the V1 retrieval / guards / generation pipeline. |
| 2026-06-21 | D-051 locked: M6 widens the dependency surface by adding `langgraph>=0.4,<0.6` to `pyproject.toml`'s runtime dependencies. The range matches the V1 "no version pinning beyond the major-minor pair" pattern. M6 does NOT commit to any future `langgraph-prebuilt` / `langgraph-checkpoint` adoption; M9+ may introduce them. |
| 2026-06-21 | M6 closed on `feat/m6-langgraph-skeleton` (not yet pushed to `main`). F-35 (channel-shape vs typed-state split, intentional two-layer separation: framework-side mutable channel + application-side immutable dataclass) raised during verification and accepted-Low per `docs/AUDITS/M6_REPORT.md`. Closure report at `docs/AUDITS/M6_REPORT.md`. Combined pytest 86 passed, 52 sandbox-skips, 0 failed. |

---

## Known Risks

- Source implementation exists at M0..M6 on `main` and a
  series of feature branches (`feat/m5-jwt-validation`,
  `feat/m6-langgraph-skeleton`). Capabilities (Embedding,
  Reranker, Guardrail, Generation) remain capability-based
  until separate ADRs are written.
- RAGAS and RBAC release-gate thresholds are not pinned.
- `uv.lock` from the M0 verification pass is untracked; its
  disposition is deferred until repository hygiene is revisited
  after M1 foundations are established.
- `skills/external/skill-creator/` is parked on disk for future
  capability building; not routed through `SKILLS.md` and not
  required by M1.
- A skeleton commit `1e6f28f` titled `Step 2 backend skeleton`
  sits in the reflog but is not reachable from `main`; ignored
  for M1.
- M1 verification (`docker compose up`, EXPLAIN, fixture load)
  must be run by a developer or in CI; the sandbox here cannot
  reach a Postgres. M1 is not claimed verified until the
  verification commands listed in
  `infrastructure/migrations/README.md` succeed end-to-end.
- M2 verification is developer-side only; the sandbox cannot
  reach the dev compose. The combined pytest report in the
  sandbox shows 52 Postgres adapter skips; this is environmental,
  not a regression.

---

## Update Rule

Update this file when a milestone starts, completes, or blocks.
Keep entries concise. Do not duplicate the milestone descriptions
that already live in `PROJECT_STATUS.md`.