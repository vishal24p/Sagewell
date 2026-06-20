# Current State

**Last updated**: 2026-06-20

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

**M2 closed. M3 (API Skeleton / FastAPI) is the next milestone.**

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

Source of truth: `PROJECT_STATUS.md` M0-M14.

---

## Completed

| Milestone | Description | Date |
|---|---|---|
| M0 | Access Decision (pure) and RBAC Access Outcome Suite. | 2026-06-19 |
| M1 | Schema, Migrations, Fixtures, Indexes. Verified via the F-21 (image tag), F-22 (healthcheck escaping), and F-23 (host port) remedies. | 2026-06-19 |
| M2 | Repositories (ports + in-memory + Postgres adapters + parity tests). Developer-side Postgres parity verified on `localhost:55432`. F-24..F-28 surfaced and resolved during the parity run. | 2026-06-20 |

### Completed In Documentation

| Item | Date |
|---|---|
| V1 architecture approved (`docs/adr/0001-...`) | 2026-06-19 |
| Documentation audit and corrections (`docs/AUDIT_REPORT.md`) | 2026-06-19 |
| Architecture verification pass (`docs/VERIFICATION_REPORT.md`) | 2026-06-19 |
| Implementation roadmap published (`PROJECT_STATUS.md` M0-M14) | 2026-06-19 |
| Roadmap refinement: JWT before LangGraph skeleton | 2026-06-19 |
| Agent-handoff refactor: `AGENTS.md` reduced to constitution, `NEXT_AGENT.md` and `docs/HANDOFF/` created | 2026-06-19 |

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
| (none) | M2 closed 2026-06-20; M3 (API Skeleton) is up next. | (none assigned) | (not started) |

---

## Recently Completed

| Date | Item |
|---|---|
| 2026-06-19 | M0 — Access Decision (pure) implemented as `src/domain/access/` with `Clearance` enum, `User`/`Document` value types, and `decide(user, document) -> (allowed, reason)`. RBAC Access Outcome Suite placed at `tests/rbac/test_access_decision.py` (31/31 passing). Function is pure: no framework imports, no database calls. Missing authorization inputs fail closed with explicit reason codes. Role-regression test confirms `users.role` does not influence the decision. |
| 2026-06-19 | M1 — Schema, Migrations, Fixtures, Indexes authored (unverified from the sandbox). Docker compose at `docker/compose.dev.yml` brings up Postgres + ParadeDB `pg_search`. Migrations `001_extensions`, `002_schema`, `003_indexes`, `004_fixtures` are reversible SQL pairs under `migrations/`. Fixtures are SQL under `db/fixtures/` and use a `fixture-` prefix and `source_system='fixture'` so rollback does not touch real data. Apply and rollback run via `infrastructure/migrations/{apply,rollback}.sh`. ADRs `0002-pg-search-paradedb.md` and `0003-raw-sql-migrations.md` capture the M1 decisions. Verification requires a Postgres reachable from a developer environment; the sandbox does not run Docker. |
| 2026-06-20 | M2 — Repositories (ports + in-memory + Postgres adapters + parity tests) implemented and developer-side verified on `localhost:55432`. RBAC Access Outcome Suite remains 31/31 green. Combined pytest: 81 passed, 2 by-design skips, 0 failed, 0 errors. Findings F-24..F-28 surfaced and resolved during the parity run. M2 status flips from `Implemented, Verified Ready` to `Closed`. |

---

## Not Started

| Milestone | Description |
|---|---|
| M3 | API Skeleton. |
| M4 | Audit Infrastructure. |
| M5 | JWT Validation. |
| M6 | LangGraph Skeleton (actor-aware). |
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
| 2026-06-20 | M2 closed. Developer-side parity run on `localhost:55432` reported 50/52 repository tests passed (2 by-design skips, 0 failed, 0 errors), and combined pytest 81 passed / 2 skipped. M3 (API Skeleton) is the next milestone. |
| 2026-06-20 | AuditLogRepository enforces the seven M0 IMM reason codes at append time. Other strings rejected with `PersistenceError`. |

---

## Known Risks

- Model capabilities (Embedding, Reranker, Guardrail, Generation)
  remain capability-based until separate ADRs are written.
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

---

## Update Rule

Update this file when a milestone starts, completes, or blocks.
Keep entries concise. Do not duplicate the milestone descriptions
that already live in `PROJECT_STATUS.md`.