# M1 Engineering Findings

**Date**: 2026-06-19
**Scope**: M1 deliverables under `migrations/`, `db/fixtures/`,
`docker/`, `infrastructure/migrations/`.
**Method**: Read every author-side file. Cross-check ownership and
robustness against `DATABASE_SCHEMA.md`, `POLICIES.md`, `WORKFLOWS.md`,
`ARCHITECTURE.md`, and `AGENTS.md`.

Findings are tagged **CRITICAL** (blocks verification),
**HIGH** (incorrect schema or unsafe behaviour), **MEDIUM**
(portability or quality), **LOW** (documentation / clarity).

---

## F-1 — `users.external_subject` has no uniqueness constraint

**Tag**: HIGH
**Location**: `migrations/002_schema.up.sql`, `DATABASE_SCHEMA.md`.

**Finding**: `users.external_subject` is the identity subject and is
the unique handle used by JWT lookups in M5. There is no
`UNIQUE` constraint on the column. A second row with the same
`external_subject` would slide in silently. Lookup by
`external_subject` would need to discriminate between rows,
producing nondeterministic JWT-to-user mapping and a possible
authorization bypass if an attacker can register an alternate
`external_subject` for the same identity.

**Required fix**: add `CONSTRAINT users_external_subject_unique UNIQUE (external_subject)`
on the `users` table. Document the determination in `DATABASE_SCHEMA.md`
and the ADR.

---

## F-2 — `users.email` uniqueness not pinned

**Tag**: MEDIUM
**Location**: `migrations/002_schema.up.sql`.

**Finding**: The schema narrative does not say whether two rows
with the same `email` are allowed. In practice, an enterprise IAM
layer will treat email as a globally unique identifier; without a
constraint at the schema level, fixture duplicates silently
succeed.

**Required fix**: add `CONSTRAINT users_email_unique UNIQUE (email)` on
the `users` table. Document in `DATABASE_SCHEMA.md`.

---

## F-3 — `chunks.embedding` dimensionality is unbounded; HNSW index assumes a dimension

**Tag**: HIGH
**Location**: `migrations/002_schema.up.sql`, `migrations/003_indexes.up.sql`.

**Finding**: `chunks.embedding` is declared as `vector` with no
dimensionality argument. The HNSW index
(`chunks_embedding_idx USING hnsw (embedding vector_cosine_ops)`)
also leaves the dimension implicit. `pgvector` picks a default
when the column is `vector` without a dimension argument. The
retrieval milestone expects a single, fixed dimension per row so
that dense retrieval can compute cosine similarity against a
consistent vector space.

If two rows have different embedding dimensions, the cosine operator
errors at query time with `different vector dimensions`. The defense
against this is a column-level dimension constraint (`vector(N)`).

The V1 Embedding Model capability will pin the dimension through
`D-002` (Open Question). The schema must reflect whatever value
`D-002` produces.

**Required fix**: replace `embedding vector` with
`embedding vector(1536)` (matches the candidate range in `MEMORY.md`
open questions; choose the value the user confirms), and document
the rationale in `DATABASE_SCHEMA.md`. If the user defers pinning
to `D-002`, change the column to `vector` plus a CHECK constraint
that `vector_dims(embedding) = 1536` (or a placeholder constant);
do not ship without one.

---

## F-4 — `audit_logs.reason_code` has no completeness check

**Tag**: LOW
**Location**: `migrations/002_schema.up.sql`.

**Finding**: `reason_code` is `TEXT NOT NULL` but no
predefined set is enforced. The user already chose TEXT-with-
no-constraint and has recorded that additional reason codes are
added per milestone. This is a working decision. **Status: NOT A
DEFECT** under the user's mandate. Documented here for
traceability only.

---

## F-5 — Migration apply script hardcodes `/workspace`

**Tag**: HIGH (portability)
**Location**: `infrastructure/migrations/apply.sh`,
`migrations/004_fixtures.up.sql`.

**Finding**: The fixture migration references files via
`\i /workspace/db/fixtures/...`. The apply script creates a
symlink temp dir at `/workspace` to make that path resolve.

Drawbacks:

- Hard-coded path. Not portable to developer machines that
  do not have a `/workspace` mount. The script only works because
  it creates that directory itself in a `mktemp -d` dir — that
  almost always resolves to `/tmp/sagewell-migrate.XXXXXX` on
  POSIX systems but the symlink target is hard-coded.
- `mktemp` on Windows MSYS / Git Bash returns
  `C:\...` style paths under `cygpath`. The `mktemp -d` call
  is not portable.
- `set -euo pipefail` is correct, but the script does not
  error-check `psql` availability until the first migration
  attempts to run.

**Required fix**: drop the `/workspace` indirection entirely.
Use `psql -v fixtures_dir=...` to bind a SQL variable and
`\i :fixtures_dir/001_users.sql` to include from a path
resolved at runtime. Or pass the fixtures directory as an
SQL variable inside `004_fixtures.up.sql`.

---

## F-6 — Apply script ignores `$SAGEWELL_MIGRATIONS_DIR` when passed something odd

**Tag**: LOW
**Location**: `infrastructure/migrations/apply.sh`.

**Finding**: No path validation on directory or absence check.
If the env var points at a non-directory, the script silently
proceeds with an empty array and exits 1 late. Not a correctness
defect, but it could fail faster.

**Status**: Acceptable. Will not fix unless required.

---

## F-7 — Rollback script does not check that the database is empty

**Tag**: MEDIUM
**Location**: `infrastructure/migrations/rollback.sh`.

**Finding**: Dropping tables in dependency order works for a
freshly applied migration stack. It does **not** verify that the
database is the target database. A developer running rollback
against a shared dev DB that holds other tenants' data would
silently drop unrelated schemas (none currently, but the
intention of the script is unclear from context).

**Required fix**: add a `--confirm` flag and a guard print
that echoes the target host / db before action and demands an
`--i-know-what-i-am-doing` env var.

---

## F-8 — Rollback safety: extension removal ordering

**Tag**: HIGH
**Location**: `migrations/001_extensions.down.sql`.

**Finding**: The down file drops `pg_search` then `vector`. Both
extensions are required by the schema's `chunks.embedding` column.
After `002_schema.down.sql` runs, the `chunks` table no longer
exists, so dropping extensions after tables at this point in the
sequence is fine. But the **order across migrations matters**:
`003_indexes.down.sql` (indexes) → `002_schema.down.sql` (tables)
→ `001_extensions.down.sql` (extensions). This is correct.

But `001_extensions.down.sql` lacks `CASCADE` on `DROP EXTENSION`
in the documented narrative. **The script does not trust CASCADE**;
it correctly assumes the tables are dropped first. All good.

**Required fix (documentation only)**: add a comment in
`001_extensions.down.sql` calling out the **require** that
`002_schema.down.sql` runs first.

---

## F-9 — Fixture deterministic anchor (users fixture has redundant identifiers)

**Tag**: MEDIUM
**Location**: `db/fixtures/001_users.sql`.

**Finding**: The fixture UPSERT uses `ON CONFLICT DO NOTHING`,
which silently no-ops on (impossibly) duplicate rows. If a user
inadvertently runs the apply script twice and fixture rows are
deleted between, the rollback + re-apply round-trip is
deterministic; but if the fixture rows are not deleted first,
this is a silent skip. Not a defect, but a reliability hazard.

**Status**: Acceptable. Documented.

---

## F-10 — `users.role` enum

**Tag**: LOW
**Location**: `migrations/002_schema.up.sql`.

**Finding**: `users.role` is `TEXT`. The narrative says it is
allowed to be one of `employee`, `manager`, `admin`. A constraint
would prevent typos from reaching the audit log. But the user
already chose TEXT-with-no-constraint at the schema level
(mirror of F-4). **Status: NOT A DEFECT under user's mandate.**

---

## F-11 — `chunks.document_id` should make soft-delete semantic

**Tag**: MEDIUM
**Location**: `migrations/002_schema.up.sql`, `WORKFLOWS.md`.

**Finding**: With `ON DELETE RESTRICT`, a deleted `documents` row
still appears as a parent row. Soft-delete is on
`documents.status`. The narrative references "Deleted documents
do not leave active chunks searchable" (DATABASE_SCHEMA.md), but
the schema does not enforce that. A `WHERE documents.status = 'active'`
clause belongs in retrieval queries, which is application-side —
fine — but the migration should at least mark the contract on
both tables' `status` columns. The narrative already names the
columns; this is a documentation enforcement.

**Required fix (no SQL change)**: document in MIGRATION_CHECKLIST
that retrieval-side queries must filter on `documents.status =
'active'` and `chunks.status = 'active'`.

---

## F-12 — HNSW index on empty / null `embedding` rows

**Tag**: LOW (likely a non-issue)
**Location**: `migrations/003_indexes.up.sql`.

**Finding**: HNSW indexes tolerate NULL vectors. `pgvector`
treats NULL as not-included-in-the-index. Queries still work.
Fixture rows have `embedding NULL`. No defect.

**Status**: Acceptable.

---

## F-13 — Identity column uniqueness across multi-issuer

**Tag**: LOW (concerns a future milestone; noted for tracing)
**Location**: `migrations/002_schema.up.sql`,
`DATABASE_SCHEMA.md` (users.external_subject description).

**Finding**: `external_subject` uniqueness per row may be
inadequate in a multi-issuer future where two IdPs can issue
the same `external_subject` value. For V1 single-company
single-tenant this is acceptable; for a future external-IAM
ADR this must become `(external_subject, issuer)`.

**Status**: Acceptable for V1; documented.

---

## F-14 — Compose file copies dev credentials literally

**Tag**: HIGH (security-by-construction)
**Location**: `docker/compose.dev.yml`.

**Finding**: The compose file embeds `POSTGRES_PASSWORD: sagewell_dev`
explicitly. While the file header labels it dev-only and the
migration tooling does not read the compose, a developer's
`docker compose up` does seed a database with predictable
credentials. **For dev only, acceptable.** If a developer points
their IDE at this compose in a non-dev context, the credentials
are public.

**Status**: Acceptable for dev; documented in the file header.
Will be hardened when a deployment ADR lands.

---

## F-15 — `documents.id BIGSERIAL` precision

**Tag**: LOW
**Location**: `migrations/002_schema.up.sql`.

**Finding**: `BIGSERIAL` (8 bytes) is large enough for any realistic
corpus. Not a defect; documenting.

---

## F-16 — Audit log FK target

**Tag**: LOW (defensive design)
**Location**: `migrations/002_schema.up.sql`.

**Finding**: `audit_logs.actor_user_id` is null-able per the
schema narrative ("if available"). With `RESTRICT`, an audit row
referencing a user that gets soft-deleted still holds a valid FK.
Nulling the FK on user soft-delete would not be safe because
audit rows are append-only and the actor must be retained for
compliance. RESTRICT is correct.

**Status**: Acceptable.

---

## F-17 — No `users.updated_at` trigger

**Tag**: MEDIUM
**Location**: `migrations/002_schema.up.sql`.

**Finding**: Both `users.updated_at` and `documents.updated_at`
have a default of `now()` but are not auto-updated on UPDATE. The
application is responsible for setting `updated_at` on every
update. Without a trigger, a row's `updated_at` will read as its
insertion time after the row is updated.

**Required fix**: add a `BEFORE UPDATE` trigger that sets
`updated_at = now()`. Apply to `users` and `documents`.

---

## F-18 — `updated_at` trigger is necessary on `users` only

**Tag**: LOW
**Location**: `migrations/002_schema.up.sql`.

**Finding**: `chunks` does not carry `updated_at`. `audit_logs`,
`retrieval_logs`, `evaluation_results` are append-only; no
`updated_at` is needed. Confirmed in `DATABASE_SCHEMA.md`.

**Status**: Acceptable.

---

## F-19 — Migration 003 (indexes) is idempotent on re-run, but the HNSW creation cost

**Tag**: LOW
**Location**: `migrations/003_indexes.up.sql`.

**Finding**: `CREATE INDEX IF NOT EXISTS` is idempotent for the
catalog state, but rebuilding an HNSW index (after a failed
DROP) is expensive. Acceptable for V1 dev. Documented.

**Status**: Acceptable.

---

## F-20 — `chunks.text_search` column is TEXT, not `tsvector`

**Tag**: MEDIUM
**Location**: `migrations/002_schema.up.sql`.

**Finding**: `DATABASE_SCHEMA.md` (line 96) names `text_search` as
the lexical search column. With ADR-0002 pinning to ParadeDB
`pg_search`, the column type should match `pg_search`'s expected
type. `pg_search` operates on `text` columns OR it builds a BM25
index that does its own internal indexing. The migration notes
that "lexical index details follow the chosen pg_search
integration" — but the column type is not pinned.

**Required fix**: document that `text_search` accepts plain text
input and the BM25 index uses `pg_search`'s `CREATE INDEX` on
that column. No SQL change required yet.

---

## Summary

- Critical: 0
- High: 5 (F-1, F-3, F-5, F-8 [doc-side], F-14 [doc-side])
- Medium: 6 (F-2, F-7, F-9, F-11, F-17, F-20)
- Low: 9

The high-severity portability and schema-correctness findings
(F-1, F-3, F-5, F-17) will be fixed in this remediation pass.
The remaining items are documented for their owning milestones
or accepted as-is.
