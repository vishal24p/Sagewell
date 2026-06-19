# NEXT_AGENT

This file is the operational entry point for a new agent. It answers
one question: "what is the next task, and what do I need to know to
do it?"

Read `AGENTS.md` first. Read `docs/HANDOFF/CURRENT_STATE.md` for a
snapshot of progress. Read the files listed under "Relevant
Documents" before doing anything.

---

## Current Milestone

**M1 — Schema, Migrations, Fixtures, Indexes.**

---

## Current Status

**In progress.** M0 closed on 2026-06-19 (commit `a78e21c`).
The RBAC Access Outcome Suite passes 31/31 inside the project
`.venv`. The M0 handoff record is in `docs/HANDOFF/CURRENT_STATE.md`.

---

## Next Task

Lock the V1 data contract: six tables, the `pgvector` and
`pg_search` extensions, the four V1 indexes enumerated in
`DATABASE_SCHEMA.md`, reversible migrations, and a fixture
strategy that supports M2 repositories and the release gate.

### Task definition

1. Provision the V1 database contract: extensions, schemas,
   tables, columns, constraints, foreign keys, indexes.
2. Provide reversible migrations for every change. Migrations
   must pass `apply then rollback` from a clean database.
3. Provide loadable fixtures that downstream milestones can use
   to exercise repositories without drafting data of their own.
4. Provide a verification path for the indexes named in
   `DATABASE_SCHEMA.md` (including EXPLAIN-style acceptance).

### How to test (when a database is wired)

- Migrations apply cleanly on a clean Postgres database.
- Migrations roll back to the pre-migration state.
- The `chunks` HNSW index is present after migrations.
- The `documents_access_filter_idx` is present after migrations
  and is used by an EXPLAIN check.
- Fixtures load via a documented command and the load is repeatable.

### How to verify before moving on

- Schema contract matches `DATABASE_SCHEMA.md` exactly.
- Migration tool is named and recorded in `MEMORY.md`.
- `pg_search` version pinned in `MEMORY.md`.
- `reason_code` enum is enumerated and recorded in `MEMORY.md`.
- Fixture strategy recorded in `MEMORY.md`.
- Index strategy recorded in `MEMORY.md`.
- All M1 prerequisites catalogued above are resolved (or
  recorded as new D-IDs in `DECISIONS_PENDING.md`).

---

## Relevant Documents

Read these before starting:

- `DATABASE_SCHEMA.md` — the V1 table list and index plan.
- `PROJECT_STATUS.md` — M1 milestone description and exit criteria.
- `POLICIES.md` — least-privilege account rule.
- `WORKFLOWS.md` — ingestion flow, audit logging, and citation
  verification that the schema must support.
- `skills/project/database_design/SKILL.md` — V1 schema, migrations,
  indexes.
- `docs/adr/` — accepted ADRs and ADR template; M1 may require
  new ADRs.

Do not yet read retrieval, ingestion, debugging, evaluation, or
external API skills. They are for later milestones.

---

## Do Not Touch

The items in M0's "Do Not Touch" apply. Additions for M1:

- M2 Repositories. Wait for M1.
- M3 API Skeleton. Wait for M2.
- M4 Audit Infrastructure. Wait for M3.
- Application-layer code.
- LangGraph.
- LlamaIndex.

---

## Exit Criteria

M1 is complete when all of the following are true:

- The V1 schema is recorded in migration files and the local
  Postgres database reflects it.
- All migrations roll back to a clean state, then re-apply.
- All four indexes named in `DATABASE_SCHEMA.md` exist after
  apply.
- Fixture load is documented and reproducible.
- All M1 prerequisites noted in the verification section of
  `docs/HANDOFF/CURRENT_STATE.md` have resolutions recorded in
  this file or in `DECISIONS_PENDING.md`.

Advance to M2 by updating `NEXT_AGENT.md`, `CURRENT_STATE.md`,
and appending a row to `MEMORY.md`.

---

## Known Open Questions

The M0 list still applies. In addition, M1 introduces:

- Which migration tool (raw SQL, Alembic, sqlx, dbmate, ...).
- Which Postgres version and which `pg_search` distribution
  (ParadeDB / older forms).
- Whether to use a Postgres ENUM type for `reason_code` or a
  text column with a CHECK constraint.
- Fixture layout: where, format, and how loaded.
- Whether the M1 dev DB is shared or each milestone resets it.

These block M1 implementation. They are not yet D-IDs in
`DECISIONS_PENDING.md`.