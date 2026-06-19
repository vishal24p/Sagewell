# Current State

**Last updated**: 2026-06-19

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

**M1 — Schema, Migrations, Fixtures, Indexes (unverified).**

Authoring complete. Verification commands documented in
`infrastructure/migrations/README.md` must be run by a
developer or in CI; the local sandbox cannot reach a Postgres.
M1 will not be marked verified until those commands succeed
end-to-end.

Full milestone list: `PROJECT_STATUS.md` (M0-M14).

---

## Completed

| Milestone | Description | Date |
|---|---|---|
| M0 | Access Decision (pure) and RBAC Access Outcome Suite. | 2026-06-19 |

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
| M1 | Schema, Migrations, Fixtures, Indexes. | (none assigned) | 2026-06-19 |

---

## Recently Completed

| Date | Item |
|---|---|
| 2026-06-19 | M0 — Access Decision (pure) implemented as `src/domain/access/` with `Clearance` enum, `User`/`Document` value types, and `decide(user, document) -> (allowed, reason)`. RBAC Access Outcome Suite placed at `tests/rbac/test_access_decision.py` (31/31 passing). Function is pure: no framework imports, no database calls. Missing authorization inputs fail closed with explicit reason codes. Role-regression test confirms `users.role` does not influence the decision. |
| 2026-06-19 | M1 — Schema, Migrations, Fixtures, Indexes authored (unverified from the sandbox). Docker compose at `docker/compose.dev.yml` brings up Postgres + ParadeDB `pg_search`. Migrations `001_extensions`, `002_schema`, `003_indexes`, `004_fixtures` are reversible SQL pairs under `migrations/`. Fixtures are SQL under `db/fixtures/` and use a `fixture-` prefix and `source_system='fixture'` so rollback does not touch real data. Apply and rollback run via `infrastructure/migrations/{apply,rollback}.sh`. ADRs `0002-pg-search-paradedb.md` and `0003-raw-sql-migrations.md` capture the M1 decisions. Verification requires a Postgres reachable from a developer environment; the sandbox does not run Docker. |

---

## Not Started

| Milestone | Description |
|---|---|
| M2 | Repositories. |
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