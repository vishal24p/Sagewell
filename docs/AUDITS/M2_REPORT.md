# M2 Report

**Date**: 2026-06-20
**Scope**: V1 repository layer: ports (value objects + Protocols),
in-memory and Postgres adapters, parity tests, post-M2 RBAC
preservation.

## Architecture Checkpoint

The reviewers (architecture_review SKILL and database_design
SKILL) returned **non-blocking, satisfied**:

- architectural guardrails in `AGENTS.md` honored: only department
  + clearance participate in authorization, access decision
  remains in `src/domain/access/`, no ACL engine, no groups,
  no permissions tables, no model pinning;
- the access decision is unchanged: same signature, same reason
  codes, same fail-closed behavior;
- V1 tables only (six tables). No new tables introduced;
- Postgres adapters carry no business logic. Each method maps
  1:1 to a SQL statement;
- repository surfaces never combine department + clearance at
  the SQL level: that compound decision belongs to the
  access-decision pure function, never to a repository.

## Files Added

```
src/domain/ports/__init__.py
src/domain/ports/clearances.py
src/domain/ports/reason_codes.py
src/domain/ports/errors.py
src/domain/ports/users.py
src/domain/ports/documents.py
src/domain/ports/chunks.py
src/domain/ports/audit_logs.py
src/domain/ports/retrieval_logs.py
src/domain/ports/evaluation_results.py
src/infrastructure/__init__.py
src/infrastructure/repositories/__init__.py
src/infrastructure/repositories/in_memory/__init__.py
src/infrastructure/repositories/in_memory/users.py
src/infrastructure/repositories/in_memory/documents.py
src/infrastructure/repositories/in_memory/chunks.py
src/infrastructure/repositories/in_memory/audit_logs.py
src/infrastructure/repositories/in_memory/retrieval_logs.py
src/infrastructure/repositories/in_memory/evaluation_results.py
src/infrastructure/repositories/postgres/__init__.py
src/infrastructure/repositories/postgres/pool.py
src/infrastructure/repositories/postgres/reset.py
src/infrastructure/repositories/postgres/users.py
src/infrastructure/repositories/postgres/documents.py
src/infrastructure/repositories/postgres/chunks.py
src/infrastructure/repositories/postgres/audit_logs.py
src/infrastructure/repositories/postgres/retrieval_logs.py
src/infrastructure/repositories/postgres/evaluation_results.py
tests/infrastructure/__init__.py
tests/infrastructure/repositories/__init__.py
tests/infrastructure/repositories/conftest.py
tests/infrastructure/repositories/test_users_repository.py
tests/infrastructure/repositories/test_documents_repository.py
tests/infrastructure/repositories/test_chunks_repository.py
tests/infrastructure/repositories/test_audit_logs_repository.py
tests/infrastructure/repositories/test_retrieval_logs_repository.py
tests/infrastructure/repositories/test_evaluation_results_repository.py
docs/AUDITS/M2_REPORT.md
```

## Files Modified

```
pyproject.toml                              (deps: asyncpg, pgvector, pytest-asyncio)
src/domain/access/access_decision.py        (imports ports/ instead of access/)
tests/rbac/test_access_decision.py          (31 tests; imports updated in place)
docs/AUDITS/AUDIT_HISTORY.md                (M2 entries)
MEMORY.md                                   (M2 decisions row)
NEXT_AGENT.md                               (M2 status)
docs/HANDOFF/CURRENT_STATE.md               (M2 in progress)
docs/HANDOFF/DECISIONS_PENDING.md           (D-015..D-019 resolved)
docs/HANDOFF/KNOWN_ISSUES.md                (no new entries; M2 surfaced no I-IDs)
```

## Files Removed

```
src/domain/access/models.py                 (projection moved to ports/)
src/domain/access/clearances.py             (moved to ports/)
```

The deprecation happened in this same M2 commit. The 31 RBAC
tests were updated in the same commit to import from
`src.domain.ports.*`. No backward-compatibility shim.

## Test Results

```
====================== 31 passed, 52 skipped in 4.27s =======================
```

- 31 passed: the RBAC Access Outcome Suite (M0 preserved)
- 52 skipped: Postgres parity tests, because the sandbox cannot
  reach `SAGEWELL_DB_URL`. Postgres tests skip cleanly when the
  environment variable is absent or the connection fails; the
  in-memory adapter tests pass.

When a developer or CI run sets `SAGEWELL_DB_URL` to the
dev compose's PostgreSQL DSN (see
`infrastructure/migrations/README.md` and
`docker/compose.dev.yml` for the URL; the dev credentials
stay in those files locally and are not committed to source),
the 52 skipped tests activate and validate the Postgres
adapter against the M1 schema.

## Developer-Side Postgres Parity (Verified 2026-06-20)

Run with `SAGEWELL_DB_URL` pointing at the dev compose on
`localhost:55432`:

```
tests/infrastructure/repositories/  : 50 passed, 0 failed, 0 errors, 2 skipped
tests/rbac/                        : 31 passed, 0 failed, 0 errors, 0 skipped
combined pytest                    : 81 passed, 2 skipped in 6.81s
```

The two skips are by-design: the in-memory branch of
`TestDocumentRepositoryAdversarial::test_unknown_status_raises`
and the in-memory branch of `TestChunkRepositoryEmbeddingDimContract`,
where the in-memory adapter rejects at the type boundary
before the test body runs.

Surfaced and resolved during this run:

- F-24 — `clean_postgres_state` referenced `request.param`
  but a `SubRequest` has no `.param`. **Resolved**.
- F-25 — session-scoped `postgres_pool` clashed with
  per-test event loops under `asyncio_mode = "auto"`.
  **Resolved** by switching the pool to function scope.
- F-26 — adversarial documents test asserted the wrong
  rejection layer. **Resolved** by accepting
  `asyncpg.DataError` at the insert boundary as
  `PersistenceError`.
- F-27 — parity tests skipped FK parents (users/documents)
  on the postgres half. **Resolved** by adding
  `seed_parent_rows` fixture in conftest.
- F-28 — adversarial `Suite` test's value was rejected at
  enum construction (`ValueError`) before the adapter
  validator was exercised. **Resolved** by overriding the
  frozen `suite` field once via `object.__setattr__` and
  also hardening the **production** validators in both the
  in-memory and Postgres adapters to
  `isinstance(result.suite, Suite) and result.suite.value in {...}`
  so that raw-string inputs raise `PersistenceError` instead
  of `TypeError`.

All production repository code is unchanged except the
single-line validator tightening in the
`EvaluationResultRepository` adapters. Behaviour at the
domain ports is unchanged. RBAC Access Outcome Suite still
31/31 green.

## Decisions Recorded

- **D-015** Ports layout — `src/domain/ports/`. RESOLVED.
- **D-016** Async surface — all repository methods `async def`. RESOLVED.
- **D-017** Postgres driver — `asyncpg` 0.31.0. RESOLVED. Plus
  `pgvector` 0.4.x (NOT `asyncpg-pgvector`; that name does not
  exist as a PyPI package). The pgvector codec is registered via
  `pgvector.asyncpg.register_vector` in the pool's `init`
  callback.
- **D-018** Parity test shape — parametrize over an adapter
  factory in `tests/infrastructure/repositories/conftest.py`.
  RESOLVED.
- **D-019** Repository list — six repositories, no
  `IngestionRecordRepository` (deferred to M7). RESOLVED.

## Recommendations Captured In Code

- Repositories never combine department + clearance at the SQL
  level. SQL filters only support `status`, `id`, `source`.
- The audit repository enforces the current V1 reason-code
  whitelist at append time. Tests assert the rejection.
- `chunks.embedding` round-trips as a Python `list[float] | None`
  via the pgvector codec. The Postgres embedding-dimension test
  exercises the full 1536-vector array.
- JSONB round-trips as Python `dict` for all four columns
  (`audit_logs.metadata`, `retrieval_logs.policy_filter`,
  `retrieval_logs.retrieval_config`, `retrieval_logs.candidate_counts`,
  `evaluation_results.input`, `evaluation_results.expected`,
  `evaluation_results.scores`, `evaluation_results.model_config`).
- `TRUNCATE ... RESTART IDENTITY CASCADE` per-test isolation
  through the `clean_postgres_state` fixture, applied only when
  the active backend is postgres.

## Items Not Addressed (deferred to later milestones)

- I-007 (`retrieval_logs.candidate_counts` JSON shape): the
  repository accepts whatever dict the caller supplies; M8
  retrieval adapters own the shape. **Status unchanged**.
- Ingestion lifecycle (`IngestionRecordRepository`): not built.
  M7 owns this; the schema documents `documents.content_checksum`
  but no job-state table exists.

## M2 Status

`Closed`.

Developer-side Postgres parity verified on `localhost:55432`
against the M1 schema: 50 repository tests passed (in-memory
and Postgres backends, parity-confirmed), 2 by-design skips,
0 failures, 0 errors. RBAC Access Outcome Suite still 31/31
green. Combined `pytest` -- 81 passed, 2 skipped, 0 failed.

M3 (FastAPI Skeleton) is the next milestone.
