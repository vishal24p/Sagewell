# Memory

Authoritative project decisions, assumptions, and open questions for
Sagewell V1. Architecture decision records live in `docs/adr/`.

## Current Baseline

- Single-company, single-tenant Enterprise RAG.
- Authorization: department + clearance only.
- Retrieval: dense + BM25 + RRF fusion + cross-encoder reranking.
- Workflow orchestration: LangGraph.
- Document loading, semantic chunking, ingestion, retrieval
  abstractions: LlamaIndex.
- Data store: PostgreSQL with `pgvector` and `pg_search`.
- Authentication: JWT.
- Prompt protection: regex guard and LLM guard on the primary
  request path.
- Evaluation: RAGAS and the RBAC Access Outcome Suite (both required).
- Models: capability-based. Generation Model, Embedding Model,
  Reranker Model, Guardrail Model.
- V1 tables: users, documents, chunks, audit_logs, retrieval_logs,
  evaluation_results.

## Accepted Decisions

| Date | Decision | Record |
|---|---|---|
| 2026-06-19 | V1 architecture is single-company, single-tenant, with department and clearance as the only authorization inputs, hybrid retrieval (dense + BM25 + RRF + cross-encoder), LangGraph orchestration, LlamaIndex for document loading, semantic chunking, ingestion, and retrieval abstractions, JWT authentication, regex guard and LLM guard on the primary request path, RAGAS and RBAC Access Outcome Suite evaluation, and capability-based model references. | `docs/adr/0001-single-tenant-enterprise-rag-baseline.md` |
| 2026-06-19 | `MEMORY.md` is the authoritative decisions log. `context/decisions.md` is a pointer to this file. | This file |
| 2026-06-19 | Local skills are the source of routing. `skills/project/` for project skills, `skills/external/` for vendored external skills. Do not depend on outside installed skill paths for this project. | `SKILLS.md` |
| 2026-06-19 | Project name is Sagewell. Intended GitHub repository name is `sagewell`. Do not rename the local workspace directory. | `README.md` |
| 2026-06-19 | V1 implementation sequencing: JWT validation is introduced before the LangGraph skeleton. The LangGraph state is typed with `user_id`, `department`, `clearance`, `role`, and `correlation_id` from the first test. Anonymous workflow execution is impossible. The full milestone list M0-M14 is in `PROJECT_STATUS.md`. | `PROJECT_STATUS.md` |
| 2026-06-19 | Agent-handoff architecture: `AGENTS.md` is the project constitution (permanent rules only). `NEXT_AGENT.md` carries the operational entry point. `docs/HANDOFF/CURRENT_STATE.md`, `docs/HANDOFF/DECISIONS_PENDING.md`, and `docs/HANDOFF/KNOWN_ISSUES.md` carry progress, pending decisions, and unresolved engineering concerns respectively. | `AGENTS.md`, `NEXT_AGENT.md`, `docs/HANDOFF/` |
| 2026-06-19 | M0 access decision is a pure function at `src/domain/access/access_decision.py` with signature `decide(user, document) -> (allowed, reason)`. Stable reason codes: `allowed`, `department_mismatch`, `clearance_insufficient`, `missing_user_department`, `missing_user_clearance`, `missing_document_department`, `missing_document_clearance`. Missing inputs fail closed (deny, never raise). The RBAC Access Outcome Suite lives at `tests/rbac/` and must reach 100% pass before advancing to M1. `users.role` is excluded from the decision and guarded by a role-regression test. | `src/domain/access/`, `tests/rbac/` |
| 2026-06-19 | V1 lexical retrieval relies on ParadeDB `pg_search`. The M1 migration creates the extension with `IF NOT EXISTS` and does not pin a specific version; version pinning is owned by deployment/infrastructure, not the schema. ADR-0002 records the decision. | `docs/adr/0002-pg-search-paradedb.md` |
| 2026-06-19 | Migrations are raw numbered SQL pairs (`migrations/NNN_*.up.sql` and `NNN_*.down.sql`) under `migrations/`. Run tooling lives in `infrastructure/migrations/{apply,rollback}.sh` and uses `psql` only. No Alembic, SQLAlchemy, `dbmate`, `yoyo-migrations`, or `sqitch` is introduced. ADR-0003 records the decision. | `docs/adr/0003-raw-sql-migrations.md` |
| 2026-06-19 | M1 fixtures carry an `external_subject` prefix of `fixture-` on `users` and `source_system='fixture'` on `documents`/`chunks`. The fixture sheet never adds columns to the canonical schema in `DATABASE_SCHEMA.md`; the prefix is the rollback boundary. | `db/fixtures/` |
| 2026-06-19 | M1 FK behavior is RESTRICT on every cross-table reference (`chunks.document_id`, `audit_logs.actor_user_id`, `retrieval_logs.actor_user_id`). Application soft-delete via the `status` column is the cancel path. | `migrations/002_schema.up.sql` |
| 2026-06-19 | `audit_logs.reason_code` is stored as TEXT with no DB-level constraint; application code is responsible for emitting only the M0-imm reason codes (`allowed`, `department_mismatch`, `clearance_insufficient`, `missing_user_department`, `missing_user_clearance`, `missing_document_department`, `missing_document_clearance`). Additional reason codes are added in their own milestones. | `migrations/002_schema.up.sql` |
| 2026-06-19 | M1 schema fixes: `users.external_subject` and `users.email` are UNIQUE; `chunks.embedding` is `vector(1536)`; `users.updated_at` and `documents.updated_at` are kept current by BEFORE UPDATE triggers via `sagewell_touch_updated_at`. | `migrations/002_schema.up.sql`, `docs/adr/0004-embedding-dimension-1536.md` |
| 2026-06-19 | Migration runners are portable. Apply sets `:fixtures_dir` via `psql -v`; rollback requires the explicit `SAGEWELL_ROLLBACK_CONFIRM=I_UNDERSTAND`. | `infrastructure/migrations/`, `docs/AUDITS/FINDINGS.md` |
| 2026-06-19 | Dev compose uses `paradedb/paradedb:pg17`. The `pg_search` extension library ships inside the image; the schema migration activates it via `CREATE EXTENSION IF NOT EXISTS pg_search`. Overridable per environment but not pinned at the schema layer. Production deployments pin by digest. ADR-0002 paragraph updated to reflect the corrected tag. Closes M1 verification failure F-21. | `docker/compose.dev.yml`, `docs/adr/0002-pg-search-paradedb.md`, `docs/AUDITS/FINDINGS.md` |
| 2026-06-19 | Dev compose healthcheck probes `pg_search` via `echo ... \| psql -tAX \| grep -q '^1$'`. Avoids YAML/shell single-quote escaping collisions that broke the previous inline `-c '... WHERE extname IN (''vector'', ''pg_search'');'` form. Closes M1 verification failure F-22. | `docker/compose.dev.yml`, `docs/AUDITS/FINDINGS.md` |
| 2026-06-19 | Dev compose publishes host port 55432 (not 5432). The host machine commonly runs a Windows-native Postgres that owns port 5432; a host `psql` session then lands on the wrong server. The dev container's Postgres is reachable via `localhost:55432` after this fix. Closes M1 verification failure F-23. | `docker/compose.dev.yml`, `infrastructure/migrations/README.md`, `docs/AUDITS/FINDINGS.md` |
| 2026-06-19 | M1 closed. Developer-side verification ran clean against the corrected image tag (`paradedb/paradedb:pg17`), the corrected healthcheck (`echo ... \| psql -tAX \| grep -q '^1$'`), and the corrected host port (55432:5432). F-21, F-22, F-23 resolved. `docs/AUDITS/M1_VERIFICATION_REPORT.md` is at status PASSED. `NEXT_AGENT.md` and `docs/HANDOFF/CURRENT_STATE.md` now carry the M2 entry point. No architectural or schema change for the M1 closure. | `NEXT_AGENT.md`, `docs/HANDOFF/CURRENT_STATE.md`, `docs/AUDITS/M1_VERIFICATION_REPORT.md`, `docs/AUDITS/MILESTONE_GATES.md`, `docs/AUDITS/AUDIT_HISTORY.md` |
| 2026-06-20 | M2 ports layer introduced at `src/domain/ports/`. Value objects (`User`, `Document`, `Chunk`, `AuditEvent`, `RetrievalLog`, `EvaluationResult`) and Protocols (`UserRepository`, `DocumentRepository`, `ChunkRepository`, `AuditLogRepository`, `RetrievalLogRepository`, `EvaluationResultRepository`) are co-located. Department + clearance access-decision is unchanged at `src/domain/access/access_decision.py`. The M0 RBAC Access Outcome Suite (31 cases) imports from the ports layer. No backwards-compatibility shim. | `src/domain/ports/`, `src/domain/access/access_decision.py`, `tests/rbac/test_access_decision.py` |
| 2026-06-20 | M2 repository drivers: `asyncpg>=0.30,<0.32`, `pgvector>=0.3,<0.5`, `pytest-asyncio>=0.23,<2.0`. The pgvector codec is registered via `pgvector.asyncpg.register_vector` (NOT a package named `asyncpg-pgvector`; that name is not on PyPI). asyncpg's `init` callback also registers the JSONB codec so `metadata`, `policy_filter`, `retrieval_config`, `candidate_counts`, `input`, `expected`, `scores`, `model_config` round-trip as Python `dict`. | `pyproject.toml`, `src/infrastructure/repositories/postgres/pool.py` |
| 2026-06-20 | M2 test isolation: per-test `TRUNCATE ... RESTART IDENTITY CASCADE` against the dev compose. Postgres adapter tests skip cleanly when `SAGEWELL_DB_URL` is unset or unreachable. Parity tests parameterize over an adapter factory in `tests/infrastructure/repositories/conftest.py`; the same test matrix runs against both backends. | `tests/infrastructure/repositories/conftest.py`, `src/infrastructure/repositories/postgres/reset.py` |
| 2026-06-20 | M2 repositories never combine department + clearance at the SQL level; that compound decision remains the access-decision pure function's responsibility. SQL filters support `status`, `id`, `source` only. `documents.find_active_by_ids` keeps the soft-delete invariant by filtering on `status='active'`. ChunkRepository's M2 scope is active-row lookups only; BM25 / dense similarity belongs to M8 retrieval adapters, not repositories. | `src/infrastructure/repositories/postgres/`, `src/infrastructure/repositories/in_memory/` |
| 2026-06-20 | AuditLogRepository append enforces the current V1 reason-code whitelist (the seven M0 IMM codes). It rejects other strings with `PersistenceError`. Tests assert the rejection. | `src/domain/ports/reason_codes.py`, `src/infrastructure/repositories/postgres/audit_logs.py`, `src/infrastructure/repositories/in_memory/audit_logs.py` |
| 2026-06-20 | M2 closed. Developer-side parity run on `localhost:55432` confirms: 50 of 52 repository tests passed (2 by-design skips, 0 failed, 0 errors), combined pytest 81 passed and 2 skipped, RBAC Access Outcome Suite still 31/31. Findings F-24..F-28 surfaced and resolved during the parity run (SubRequest.param, asyncpg pool loop-mismatch, adversarial documents test layer, FK parent seed, adversarial `Suite` test + production-side validator hardening). `tests/infrastructure/repositories/conftest.py` carries `clean_postgres_state`, `seed_parent_rows`, and a function-scoped `postgres_pool`. | `docs/AUDITS/M2_REPORT.md`, `docs/AUDITS/MILESTONE_GATES.md`, `docs/AUDITS/AUDIT_HISTORY.md`, `tests/infrastructure/repositories/conftest.py`, `src/infrastructure/repositories/{in_memory,postgres}/evaluation_results.py` |
| 2026-06-20 | `pytest-asyncio` 1.4.0 with `asyncio_mode = "auto"` defaults to per-test event loops. asyncpg pools hold connections loop-bound on first acquire. Session-scoped asyncpg pool causes `asyncpg.InterfaceError: ... another operation is in progress` and `RuntimeError: ... attached to a different loop` on the second and later postgres tests in the same session. The M2 parity suite uses function-scoped `postgres_pool` to avoid the loop mismatch. The alternative is `asyncio_default_fixture_loop_scope = "session"` at the pytest-asyncio level, deferred. | `tests/infrastructure/repositories/conftest.py`, `pyproject.toml` |
| 2026-06-20 | M3 — API Skeleton reduced to a pure API shell. Routes are exactly `GET /health`, `GET /openapi.json`, `GET /docs`, `GET /redoc`. Launch contract: `uvicorn src.api.app:create_app --factory`. No DB. No JWT. No query-answer stub. The rejected M3-item list lives in `docs/AUDITS/M3_REPORT.md`. | `docs/AUDITS/M3_REPORT.md`, `src/api/app.py` |
| 2026-06-20 | D-020 — Correlation id generator: **UUID4** (`uuid.uuid4()`). Drop UUIDv7. | `src/api/middleware/correlation.py`, `docs/AUDITS/M3_REPORT.md` |
| 2026-06-20 | D-021 — Error envelope shape: minimum `{code, message, correlation_id}`. No `details` field at M3. Domain-error translation deferred to M4. | `src/api/errors/schemas.py`, `docs/AUDITS/M3_REPORT.md` |
| 2026-06-20 | D-024 — Settings surface for M3: `SAGEWELL_LOG_LEVEL` (default `INFO`), `SAGEWELL_API_HOST` (default `127.0.0.1`), `SAGEWELL_API_PORT` (default `8000`). `SAGEWELL_CORS_ALLOWED_ORIGINS`, `SAGEWELL_TRUSTED_PROXY_HEADER`, `SAGEWELL_DB_URL` are intentionally out of M3. | `src/api/settings.py`, `docs/AUDITS/M3_REPORT.md` |
| 2026-06-20 | D-025 — Default docs surface enabled: `/docs`, `/redoc`, `/openapi.json` are on by default. | `src/api/app.py`, `docs/AUDITS/M3_REPORT.md` |
| 2026-06-20 | D-026 — Keep `src/api/__main__.py` for `python -m src.api`. | `src/api/__main__.py` |
| 2026-06-20 | D-027 — Catch-all log keys: `correlation_id`, `exception_type`, `exc_message`. The third key is named `exc_message` (not `message`) because the std-lib `LogRecord` reserves `message`; reusing it raises `KeyError("Attempt to overwrite 'message' in LogRecord")` at runtime. The D-027 *mandate* of three keys is preserved; the canonical key names live in `M3_REPORT.md`. | `src/api/errors/__init__.py`, `docs/AUDITS/M3_REPORT.md` |
| 2026-06-20 | D-028 — Forward hook: `src/api/` MUST NOT depend on the future workflow package or any other domain-derived surface. The dependency direction is `workflow -> api`, not `api -> workflow`. This guardrail pairs with the rule "no DB driver imports under `src/api/`" and ensures M3 has no opaque coupling. | `docs/AUDITS/M3_REPORT.md`, `NEXT_AGENT.md` |
| 2026-06-20 | Starlette 0.48's `ServerErrorMiddleware` always re-raises after a registered handler returns a response. FastAPI's `add_exception_handler(Exception, ...)` falls inside that flow. Uncaught-exception-to-500 therefore runs as a `BaseHTTPMiddleware` so the exception is consumed inside the request pipeline (the re-raise becomes harmless because the response has been written). Future domain-error handlers register on top of this middleware. | `src/api/errors/__init__.py` |

## Assumptions

- Department and clearance are sufficient for V1 authorization.
- A future version may introduce ACLs, groups, or external IAM. Any
  such change requires an ADR and is not in V1.
- Source implementation has not started in V1 documentation.
- A future implementation will add concrete migration, test, and
  deployment commands.
- The access decision is a single pure function invoked at every
  boundary (pre-retrieval, post-rerank, citation verification).

## Open Questions

- Which JWT signing algorithm and key management approach?
- Which Embedding Model, Reranker Model, Guardrail Model, and
  Generation Model capabilities will be adopted?
- Which `pg_search` distribution and version?
- What are the RAGAS score thresholds and the RBAC Access Outcome
  thresholds for the release gate?
- What retention policy applies to audit_logs, retrieval_logs, and
  evaluation_results?

## Update Rules

- Add concise entries when a decision affects future implementation.
- Move architectural decisions into `docs/adr/` when alternatives and
  consequences matter.
- Do not store secrets, credentials, or private customer data here.
- Do not duplicate this file. If `context/decisions.md` is updated,
  update this file instead and keep `context/decisions.md` as a
  pointer.