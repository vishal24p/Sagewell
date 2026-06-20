# NEXT_AGENT

This file is the operational entry point for a new agent. It answers
one question: "what is the next task, and what do I need to know to
do it?"

Read `AGENTS.md` first. Read `docs/HANDOFF/CURRENT_STATE.md` for a
snapshot of progress. Read the files listed under "Relevant
Documents" before doing anything.

---

## Current Milestone

**M2 — Repository Layer.**

## Current Status

**M1 closed on 2026-06-19. M2 implementation complete in working
tree as of 2026-06-20. M2 status: Implemented, Verified Ready
pending developer-side Postgres parity.**

M0 closed on 2026-06-19 (commit `a78e21c`). M1 closed on
2026-06-19 (commits `0947558`, `dc21743`, `bc8f257`, `34a1252`,
`38a1efa`, `38a1efa`). M2 implementation is not yet committed as
of `LAST_UPDATED`.

Repository ports at `src/domain/ports/`. Adapters at
`src/infrastructure/repositories/{in_memory,postgres}/`. Parity
tests at `tests/infrastructure/repositories/`. RBAC Access
Outcome Suite still 31/31 green.

M3 (API Skeleton) does not begin until M2 is Closed.

---

## Next Task

Close M2 once developer-side Postgres parity is verified; or, if
the working tree already passes, commit M2 and run the
developer-side parity. The Postgres half is the only remaining
verification: a developer or CI run exports
`SAGEWELL_DB_URL` set to the dev-compose Postgres URL (see
`infrastructure/migrations/README.md` and `docker/compose.dev.yml`;
credentials are local-dev only and should never be committed)
with the M1 migrations applied, then runs the parity suite. The
52 currently-skipped Postgres tests must turn green.

If new findings emerge during that run, surface them through
`docs/AUDITS/FINDINGS.md` with a fresh F-Id and remediate before
declaring M2 Closed.

When M2 is Closed:

1. Update `NEXT_AGENT.md` (this file) to point at M3.
2. Update `docs/HANDOFF/CURRENT_STATE.md` "Current Milestone":
   M2 → M3.
3. Append a row to `MEMORY.md` summarizing the closure.
4. Append `Verified Ready`+`Verified` rows to
   `docs/AUDITS/MILESTONE_GATES.md`.
5. Append audit history rows to
   `docs/AUDITS/AUDIT_HISTORY.md`.
6. Update `PROJECT_STATUS.md` M2 row status (Closed).
7. Then start the M3 pre-implementation review per
   `skills/project/api_skeleton/SKILL.md`.

### Task definition

1. Identify the repositories required by M2's consumers (audit
   writer, user loader, document/chunk listers, retrieval
   adapters, evaluation results, ingestion). Source each
   consumer's repository requirement explicitly from work in
   ARCHITECTURE.md and POLICIES.md, not from assumed patterns.
2. Define each repository as a `Protocol` (or `abc.ABC`) in
   `src/domain/ports/`. Domain code consumes the protocol. No
   framework imports in `src/domain/`.
3. Provide an in-memory implementation under
   `src/infrastructure/repositories/in_memory/` for each port.
4. Provide a Postgres implementation under
   `src/infrastructure/repositories/postgres/` that mirrors
   the in-memory behaviour 1:1. The Postgres implementation is
   exercised against the dev compose's `localhost:55432`
   endpoint with the M1 migrations applied.
5. Tests live under `tests/infrastructure/repositories/` with
   the RBAC Access Outcome Suite-style table-driven cases
   covering the operations M2's consumers actually need.
6. Cross-check parity at the end of M2: every in-memory test
   runs identically against the Postgres adapter against the
   dev compose.

### How to test (when ready)

- `pytest tests/infrastructure/repositories/` is green against
  the in-memory adapter.
- `pytest tests/infrastructure/repositories/` is also green
  against the Postgres adapter with `SAGEWELL_DB_URL=postgres://
  sagewell:sagewell_dev@localhost:55432/sagewell` and the M1
  migrations applied.
- No framework imports under `src/domain/`. `grep` for known
  frameworks (langchain, llama_index, asyncpg, sqlalchemy,
  alembic, fastapi) returns zero rows under `src/domain/`.

### How to verify before moving on

- Each repository protocol is documented in source comments.
- Each Postgres adapter has a parity-equivalence test against
  its in-memory counterpart.
- M0 RBAC Access Outcome Suite still passes 31/31.
- All M2 prerequisites in
  `docs/HANDOFF/DECISIONS_PENDING.md` are resolved (or moved
  to `KNOWN_ISSUES.md` if they belong to the in-flight
  milestone).

---

## Relevant Documents

Read these before starting:

- `ARCHITECTURE.md` — layered boundaries, repository direction.
- `DATABASE_SCHEMA.md` — V1 tables and columns; the Postgres
  adapter must query exactly these tables.
- `POLICIES.md` — least-privilege account rule; the
  dev-container role is `sagewell` (password `sagewell_dev`).
- `PROJECT_STATUS.md` — M2 milestone description.
- `WORKFLOWS.md` — the workflows that consume repositories
  (audit, retrieval, ingestion, evaluation).
- `skills/project/database_design/SKILL.md` — schema and
  constraint invariants.

Do not yet read retrieval, ingestion, debugging, evaluation, or
external API skills in detail. They are for M3+. M2 is canonical
infrastructure only.

---

## Do Not Touch

The items in M0's "Do Not Touch" apply. Additions for M2:

- API layer / FastAPI. Wait for M3.
- JWT validation. Wait for M5.
- LangGraph workflow. Wait for M6.
- LlamaIndex wiring. Wait for M7.
- Application-layer use cases (hand-rolled orchestration).
  Wait for M4 or M6.
- Any psycopg/asyncpg/SQLAlchemy/Alembic dependency unless
  the user has confirmed the Postgres driver choice in D-IDs.

---

## Exit Criteria

M2 is complete when all of the following are true:

- Every protocol under `src/domain/ports/` has an in-memory
  adapter under `src/infrastructure/repositories/in_memory/`.
- Every protocol under `src/domain/ports/` has a Postgres
  adapter under `src/infrastructure/repositories/postgres/`.
- Tests in `tests/infrastructure/repositories/` are green
  against both adapters.
- `src/domain/` contains zero framework imports
  (langchain, llama_index, asyncpg, sqlalchemy, alembic,
  fastapi).
- The M0 RBAC Access Outcome Suite still passes 31/31.
- A M2 closure report is committed.

Advance to M3 by updating `NEXT_AGENT.md`, `CURRENT_STATE.md`,
appending a row to `MEMORY.md`, and committing on `main`.

---

## Known Open Questions

The M0 and M1 lists still apply unless resolved. In addition,
M2 introduces:

- D-015 (Ports layout): Where should the port protocols live
  in `src/`? Choices: `src/domain/ports/`, `src/domain/repositories/`,
  or co-located with each domain entity. Affects naming.
- D-016 (Async surface): Are repository methods sync or
  `async def`? The dev compose and tests do not constrain
  this; LangGraph at M6 will likely prefer async. A sync
  repository with an async wrapper at M6 is also possible.
- D-017 (Postgres driver): Which Python driver? Choices:
  psycopg (3.x), asyncpg, psycopg2. The Postgres adapter is
  the second half of M2 and the driver choice must be locked
  before any `src/infrastructure/repositories/postgres/`
  file is written. AGENTS.md forbids introducing ORM
  dependencies silently.
- D-018 (Parity test shape): The parity test must run the
  same test matrix against the in-memory and Postgres
  adapters. Choices: parametrize over an adapter factory;
  mirror-file tests; or fixture-based pytest plugins.
- D-019 (Repository list): Which repositories are actually
  needed by M2's consumers? Today's working list (from
  WORKFLOWS.md + POLICIES.md): user_loader, audit_writer,
  document_repository, chunk_repository, retrieval_log_writer,
  evaluation_result_writer, ingestion_record_writer. Each
  must be derived, not assumed.

These block M2 implementation. They are not yet D-IDs in
`DECISIONS_PENDING.md`; the assistant surfaces them via
`AskUser` before any code change.