# Migration Checklist

**Date**: 2026-06-19

This file records what every V1 migration must satisfy. It is the
checklist used by the engineering reviewer and the developer
running verification. Migrations that violate any item are
rejected at review; migrations that pass all items and run cleanly
in the verification round-trip are marked Verified Ready.

## Per Migration

### Idempotency

- Every `up.sql` uses `CREATE EXTENSION IF NOT EXISTS`,
  `CREATE TABLE IF NOT EXISTS`, and `CREATE INDEX IF NOT EXISTS`
  where the modification is structural.
- Every `up.sql` uses `CREATE OR REPLACE FUNCTION` for shared
  trigger functions.
- Every `down.sql` uses `DROP EXTENSION IF EXISTS`,
  `DROP TABLE IF EXISTS`, `DROP INDEX IF EXISTS`,
  `DROP TRIGGER IF EXISTS` to avoid "already dropped" errors
  during repeated rollback.
- Triggers are dropped before re-creation with matching name so
  re-runs do not produce "trigger already exists".

### Atomicity

- Each migration runs in a single `--single-transaction` invocation
  by `apply.sh`. Partial-application states must not exist.

### Extension ordering

- `001_extensions.up.sql` creates `vector` then `pg_search`. Both
  are required for `002_schema.up.sql` (vector is required by
  `chunks.embedding`; `pg_search` is required by retrieval paths
  even at the migration-time level for BM25 inverted-index
  preparation referenced in M8).
- The down sequence reverses this ordering. The runner walks
  down files in reverse numerical order, which satisfies the rule.

### Table-level constraints

- Identifiers that must be unique are UNIQUE:
  - `users.external_subject`
  - `users.email`
  - (`documents.source_system`, `documents.source_id`)
- `chunks.embedding` has the fixed dimension from ADR-0004
  (`vector(1536)`).
- FKs default to `ON DELETE RESTRICT`. Application soft-delete is
  via the `status` column.

### Updated_at maintenance

- `users.updated_at` and `documents.updated_at` are kept current by
  BEFORE UPDATE triggers defined at the end of
  `002_schema.up.sql`. The trigger function is named
  `sagewell_touch_updated_at`.

### Fixture boundary

- Fixtures are not part of the canonical schema; they live
  under `db/fixtures/` and the rollback marker is the
  `external_subject LIKE 'fixture-%'` prefix on `users` and
  `source_system = 'fixture'` on `documents`/`chunks`.
- Fixture loading uses `psql -v fixtures_dir=<path>` so the
  script is portable.

### Indexes

- All four indexes named in `DATABASE_SCHEMA.md` are created in
  `003_indexes.up.sql` exactly as listed:
  - `chunks_document_id_idx`
  - `chunks_status_idx`
  - `documents_access_filter_idx`
  - `chunks_embedding_idx`
- HNSW is used for `chunks_embedding_idx` with `vector_cosine_ops`.

### Portability

- No hard-coded paths. The fixture migration uses `:fixtures_dir`
  passed by `apply.sh`.
- No machine-specific assumptions. The apply script reads
  `SAGEWELL_DB_URL`, `SAGEWELL_MIGRATIONS_DIR`,
  `SAGEWELL_FIXTURES_DIR` from the environment. No
  embedded passwords or hosts.

### Safety

- Rollback requires `SAGEWELL_ROLLBACK_CONFIRM=I_UNDERSTAND`.
- The script prints the destructive intent before the first
  rollback step.

## Round-trip Procedure

The developer-side verification must succeed for M1 to be marked
Closed. The procedure is:

1. Compose up.
2. Apply migrations.
3. Verify tables, extensions, indexes, fixtures.
4. Roll back.
5. Re-apply migrations.
6. Verify tables, extensions, indexes, fixtures are back.
7. EXPLAIN-check the access filter index.
8. Record the verification report under
   `docs/AUDITS/M1_VERIFICATION_REPORT.md` with status PASS only
   when every step above succeeds.

## Items Rejected at Review

- "Vector" columns without a dimension argument.
- Tables with FKs that depend on a column whose default has changed
  in a previous migration.
- Indexes declared in any way that prevents `IF NOT EXISTS`.
- Migration scripts that require environment variables the
  runner does not set.
- Migrations that leave tables in inconsistent partial states
  on a roll-back half-way through.
