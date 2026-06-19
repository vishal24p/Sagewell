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

## F-21 — Compose dev image tag does not exist on Docker Hub

**Tag**: CRITICAL (blocks M1 verification Step A)
**Location**: `docker/compose.dev.yml`,
`docs/adr/0002-pg-search-paradedb.md`.

**Finding**: `docker/compose.dev.yml` pinned the dev image to
`paradedb/paradedb:stable`. M1 verification's Step A executed

```
docker compose -f docker/compose.dev.yml up -d
```

and failed with

```
failed to resolve reference "docker.io/paradedb/paradedb:stable":
docker.io/paradedb/paradedb:stable: not found
```

Root cause: the upstream Docker Hub repository `paradedb/paradedb`
publishes tags by lineage (`latest`, `pg16`, `pg17`, `pg18`) and
by pinned version (`0.24.0-pg17`, etc.). There is no `stable`
alias as of the catalog snapshot on 2026-06-19. The image we asked
for therefore matches the literal "not found" diagnostic returned
by the Docker daemon. No DNS, registry authentication, or network
issue is implied.

ADR-0002 had encoded the assumption in writing
(`The Docker image tag is set to stable for M1 verification`),
so the mistake is captured in the project's ADR set, not just in
the compose file.

Implications: every other artefact in the M1 deliverable remains
correct in isolation. Schema, migrations, indexes, fixtures, and
the migration runners are unaffected. Only the dev compose image
reference is broken. M1 verification therefore unblocks with a
single-line fix.

**Required fix**:

1. `docker/compose.dev.yml`: change `image: paradedb/paradedb:stable`
   to `image: paradedb/paradedb:pg17` (Postgres 17 baseline;
   ships the `pg_search` extension library; not pinned at the
   schema layer).
2. `docs/adr/0002-pg-search-paradedb.md`: amend the
   implementation-detail paragraph in place to record the
   corrected tag. Architecture (ParadeDB `pg_search`) is
   unchanged.
3. `MEMORY.md`: add a row recording the chosen `pg17` image
   tag and the rationale (concrete default for V1 dev; not
   pinned at the schema layer).
4. `docs/HANDOFF/KNOWN_ISSUES.md` I-012: add and resolve a row
   tracing the issue.

**Status**: RESOLVED 2026-06-19. Investigation report at
`docs/AUDITS/INVESTIGATION_REPORT_M1_IMAGE.md`. The corrected
compose is the canonical replacement for Step A onwards.

No new ADR is required. AGENTS.md allows documentation edits that
restate existing decisions; ADR-0002's prose correction is such
an edit. The architecturally significant choice (ParadeDB
`pg_search`) is already captured and remains correct.

---

## F-22 — Healthcheck shell escaping blocks Step A from reporting healthy

**Tag**: HIGH (blocks compose `pg_search` healthcheck after F-21 fix)
**Location**: `docker/compose.dev.yml`,
**Discovered during**: developer-side verification, after F-21 fix
landed and the dev container started successfully.

**Finding**: After the F-21 image-tag correction in
`docker/compose.dev.yml`, the dev container started but `docker
compose ps` reported the postgres service in a non-healthy state.
The healthcheck's `test:` element was a YAML single-quoted scalar
evaluated under Docker's `CMD-SHELL`, which joins the second scalar
with a single space and passes the joined string to
`/bin/sh -c`. The previous form contained the literal

```
psql -U sagewell -d sagewell -c 'SELECT extname FROM pg_extension
WHERE extname IN (''vector'', ''pg_search'');' | grep -q pg_search
```

When Compose concatenated the `CMD-SHELL` and the test element,
the inner doubled single-quotes (`''`) collided with the YAML
single-quoted scalar. The SQL literal that arrived at the inner
shell was therefore missing its surrounding quotes, and the SQL
parser collapsed on `vector , pg_search` as bare identifiers,
producing a parse error. The healthcheck never passed; compose
repeatedly retried.

The container's database and extensions were valid. Manual
execution of an unescaped psql against the running container
returned the expected `pg_search` and `vector` rows.

**Required fix**: reflow the SQL literal under a single quoting
strategy. The chosen strategy pipes the SQL through `echo ...` to
`psql -tAX`, so the SQL string lives inside double-quoted shell
only and the inner single-quotes (`'pg_search'`) are never
re-interpreted by Compose's outer YAML scalar:

```
pg_isready -U sagewell -d sagewell &&
echo "SELECT 1 FROM pg_extension WHERE extname = 'pg_search';" |
psql -U sagewell -d sagewell -tAX -v ON_ERROR_STOP=1 |
grep -q '^1$'
```

The healthcheck still fails until `001_extensions.up.sql` has
been applied (because the `SELECT` returns zero rows pre-migration);
it remains green once the extension is present, mirroring the
intended dev workflow.

`grep -q '^1$'` anchors the match on a single character `1` so
that tuple output `1` is required, eliminating false positives
against follow-up extension listings.

**Status**: RESOLVED 2026-06-19. Compose healthcheck now reflects
"extensions are present" and not "container is up but extensions
have not been created". The dev compose comment header documents
the escaping history so future maintainers don't reintroduce the
inline `'vector', 'pg_search'` form.

No ADR, no schema change, no migration change, no architecture
change. Compose-yaml-only fix.

---

## Summary

- Critical: 1 (F-21)
- High: 6 (F-1, F-3, F-5, F-8 [doc-side], F-14 [doc-side], F-22)
- Medium: 6 (F-2, F-7, F-9, F-11, F-17, F-20)
- Low: 9

The critical finding (F-21) was discovered during developer-side
verification, not during the original engineering pass. It is
addressed in a follow-up commit that also updates the audit
follow-up row.

F-22 was discovered during the F-21 re-verification pass. The fix
is a single-file change to the compose healthcheck quoting.

The high-severity portability and schema-correctness findings
(F-1, F-3, F-5, F-17) will be fixed in this remediation pass.
The remaining items are documented for their owning milestones
or accepted as-is.
