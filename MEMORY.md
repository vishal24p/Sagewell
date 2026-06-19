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