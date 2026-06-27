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

## F-23 — Host port collision: developer machine binds 5432 with Windows-native Postgres

**Tag**: HIGH (blocks M1 verification Steps B onward)
**Location**: `docker/compose.dev.yml`,
`infrastructure/migrations/README.md`,
`docs/AUDITS/M1_VERIFICATION_REPORT.md`.
**Discovered during**: developer-side verification, after F-21 and F-22 fixes landed.

**Finding**: After F-21 (image tag) and F-22 (healthcheck quoting)
were corrected, the dev container started and reported healthy.
The developer-side verification then attempted to run

```
psql "postgresql://sagewell:sagewell_dev@localhost:5432/sagewell"
```

and observed

```
FATAL: password authentication failed for user "sagewell"
```

The previous hypothesis at this stage was a stale role password
(SCRAM/MD5 mismatch). Before applying any code, the diagnostic
was repeated under controlled conditions:

1. `docker exec sagewell-dev-postgres-1 psql -U sagwell -d sagwell -c '\dt'`
   returned the V1 tables successfully. The container's Postgres
   is healthy and the role exists.
2. `docker exec ... psql -c "SELECT extname FROM pg_extension
   WHERE extname IN ('vector', 'pg_search');"` returned both
   `pg_search` and `vector`. The database is valid.
3. `psql ...@localhost:5432` failed with the password error
   even after the dev volume had been recreated, ruling out
   the stale-volume theory (per developer confirmation).

PowerShell's `Get-NetTCPConnection -LocalPort 5432` and
`tasklist /FI "PID eq <PID>"` then resolved the conflict:

```
TCP    0.0.0.0:5432    0.0.0.0:0    LISTENING    5444    postgres.exe
TCP    [::]:5432       [::]:0       LISTENING    13400   com.docker.backend.exe
```

PID 5444 is `postgres.exe` — a Windows-native Postgres service
running on the host independently of Docker. PID 13400 is
Docker Desktop's port-forwarding process. When the host's
`psql` opens `localhost:5432`, Windows routes the TCP connection
to PID 5444 first (the host-resident listener). Docker's bridge
publishes PID 13400 *after* and is unreachable from the host's
psql session because the OS already resolved the port to PID 5444.

`ALTER USER sagwell PASSWORD 'sagewell_dev'` issued against the
container would have changed the role password successfully
inside the container, but **the developer's psql does not talk to
that database at all** — it talks to the host-resident Postgres
on PID 5444, which uses a different role namespace. The
`ALTER USER` path therefore would not have fixed the symptom.

The container's Postgres is therefore correct in itself; the
issue is the host-published port colliding with the developer's
Windows-native Postgres service.

**Required fix**: re-publish the dev compose's host port to one
that does not collide. Chosen port: **55432** (memorable; the
"5" prefix signals "Sagewell dev").

Changes:

1. `docker/compose.dev.yml`:
   - `ports` mapping is now `"55432:5432"` (was `"5432:5432"`).
   - A header comment records the rationale and warns future
     maintainers not to default to 5432 because Windows-native
     Postgres commonly claims that port on developer machines.

2. `infrastructure/migrations/README.md`:
   - The "Apply" section now mentions `localhost:55432` and
     explains why.
   - A "Prerequisites" paragraph names the F-23 collision and
     directs the developer to `docs/AUDITS/FINDINGS.md`.

3. `docs/AUDITS/M1_VERIFICATION_REPORT.md`:
   - Step A's preamble now references `localhost:55432` as the
     correct host port.
   - The report's "Findings" list absorbs this incident.

`apply.sh` is unchanged. The architecture continues to be:
Postgres in Docker, host `psql` connects, `apply.sh` targets the
URL the developer sets. The only thing the developer now sets
is the URL with port **55432** instead of 5432.

**Status**: RESOLVED 2026-06-19. Once the developer updates
`SAGEWELL_DB_URL` to use port 55432 (or applies the recipe
verbatim), Steps B onward should run cleanly.

Diagnostic commands the developer can run to confirm or rule
out this finding on a given host:

```
# Find who is bound to 5432:
Get-NetTCPConnection -LocalPort 5432 |
    Select-Object LocalAddress, LocalPort, OwningProcess
tasklist /FI "PID eq <OwningProcess>"
```

If the only listener is `com.docker.backend.exe` or `vpnkit.exe`,
the dev compose's 5432 mapping would be reachable; the
diagnosis reverts to "stale password". If the listener shows
`postgres.exe`, the port collision is the root cause and the
55432 mapping is the correct fix.

**No ADR, no schema change, no migration change, no
architecture change.** Compose-yaml-only.

---

## F-24 — `clean_postgres_state` reads `request.param` from a SubRequest

**Tag**: HIGH
**Location**: `tests/infrastructure/repositories/conftest.py`
(`fresh_postgres_state` / now `clean_postgres_state` fixture).

**Finding**: The fixture read `request.param` to skip when the
parametrized backend was `in_memory`. When the fixture was
transitively required by other fixtures (the seed-callers),
pytest handed the fixture a `SubRequest` instead of the
parent `FixtureRequest`. `SubRequest` has no `.param`, so
`request.param` raised `AttributeError: 'SubRequest' object
has no attribute 'param'`. The error propagated to every
postgres-branch test, surfacing as 50 fixture-setup ERRORS
during the developer-side run on `localhost:55432`.

**Fix**: Drop the `request.param`-driven branch. The fixture
is unconditional: it acquires the postgres pool (which
already skips on connectivity failure) and truncates the V1
tables. Rename `fresh_postgres_state` -> `clean_postgres_state`
to drop the misleading "fresh" connotation and reflect that
the fixture owns the full reset.

**Resolved**: 2026-06-20.

## F-25 — `postgres_pool` was session-scoped; clashes with per-test event loop

**Tag**: HIGH
**Location**: `tests/infrastructure/repositories/conftest.py`
(`postgres_pool` fixture, originally `scope="session"`).

**Finding**: `pyproject.toml` configures
`asyncio_mode = "auto"`. pytest-asyncio 1.x resolves each
async test to its own event loop by default. asyncpg pools
hold connections whose protocol is bound to the loop on
first acquisition. The first test's loop-bound connections
were reused on subsequent tests on different loops, producing
`RuntimeError: ... got Future attached to a different loop`
and `asyncpg.InterfaceError: cannot perform another
operation`.

**Fix**: Flip `postgres_pool` to function scope and open the
pool per-test. asyncpg pool init cost is sub-millisecond; the
52-test matrix tolerates the per-test acquire cost. The
`asyncio_default_fixture_loop_scope = "session"` global
config (alternative fix) was rejected for now because it
broadly changes pytest-asyncio's loop behavior across the
whole project; the function-scoped pool is the explicit,
local opt-in.

**Resolved**: 2026-06-20.

## F-26 — adversarial documents test asserts the wrong rejection layer

**Tag**: MEDIUM
**Location**: `tests/infrastructure/repositories/test_documents_repository.py`
(`TestDocumentRepositoryAdversarial::test_unknown_status_raises[postgres]`).

**Finding**: The test inserted a row with
`status='not-a-status'`. Because `documents.status` is the
`document_status` enum column, Postgres rejected the write
at the column cast (`asyncpg.exceptions.DataError`) before
the adapter's read-coercion path could ever be exercised.
The `pytest.raises(PersistenceError)` was attached to the
read path; the test would have passed only if the write
layer's `DataError` had been swallowed and the read-side
adapter had been reached. Both layers reject unknown enum
values; both correct failures were reachable, but only one
was being asserted.

**Fix**: Wrap the INSERT in `try/except DataError`, and on
`DataError` re-raise as `PersistenceError` so the test
contract (`PersistenceError is raised`) holds at the
write-time boundary. The read-side `pytest.raises` block
remains in place for the case where the DB write succeeds
with a valid enum (the next adversarial case to be added).

**Resolved**: 2026-06-20.

## F-27 — repository parity tests skip FK parents

**Tag**: HIGH (test infrastructure only)
**Location**: `tests/infrastructure/repositories/{test_audit_logs,test_retrieval_logs,test_chunks}_repository.py`.

**Finding**: The parity suite made its repository inserts
through direct SQL / `add()`, but the FK constraints on
`audit_logs.actor_user_id`, `retrieval_logs.actor_user_id`,
and `chunks.document_id` enforce RESTRICT. With the dev
compose reachable, the postgres half of the suite hit
`asyncpg.exceptions.ForeignKeyViolationError` on every
insert that depended on a parent row. The in-memory half was
not affected because the in-memory adapter does not enforce
FKs, so half-passes masked the real failure.

This is a test-side defect, not a production defect: the
repositories correctly expect a non-existent actor/document
to fail at the SQL boundary. Production callers (M5 +)
will not hit FK violations because they will read the actor
through `UserRepository.find_by_external_subject` first.

**Fix**: Add `seed_parent_rows` fixture in conftest that
seeds user id=1 and document id=42 against both backends
before each test that depends on them. Hook the fixture
into the three affected test classes via
`adapter, seed_parent_rows` (replacing
`adapter, clean_postgres_state` only on the dependent
fixtures).

**Resolved**: 2026-06-20.

## F-28 — adversarial `Suite` test never reaches the adapter validator

**Tag**: MEDIUM (test design only)
**Location**:
`tests/infrastructure/repositories/test_evaluation_results_repository.py`.
`TestEvaluationResultRepository::test_record_rejects_unknown_suite_value`.

**Finding**: The test constructed
`Suite("hypothetical_suite")` to bypass the enum. Python's
`Enum.__call__` rejects a string outside the declared
members with `ValueError`, and the test's
`pytest.raises(PersistenceError)` was never reached. Both
the in-memory and postgres branches failed with `ValueError`
before the adapter's internal validator (`suite in Suite`)
was exercised. The test's surface contract was wrong, not
the production code.

**Fix**: Build a valid `EvaluationResult`, then override
the frozen `suite` field once via `object.__setattr__(bad,
"suite", "hypothetical_suite")`. The adapter's validator
catches the unknown string and raises `PersistenceError`,
which the test asserts.

**Resolved**: 2026-06-20.

## F-29 - M3 catch-all log key collides with `LogRecord` reserved field

**Tag**: MEDIUM (D-027 implementation drift)
**Location**: `src/api/errors/__init__.py`.
`catch_all_exception_handler` (later folded into the
`BaseHTTPMiddleware` in M3).

**Finding**: The D-027 mandate specified three log keys:
`correlation_id`, `exception_type`, `message`. Implementing
the handler with `logger.error("api.unhandled_exception",
extra={"correlation_id": cid, "exception_type":
type(exc).__name__, "message": str(exc)})` raised
`KeyError("Attempt to overwrite 'message' in LogRecord")`
at runtime when the catch-all fired. The std-lib
`LogRecord.__init__` rejects `extra` keys that collide
with its reserved fields (`message`, `asctime`, etc.).

**Fix**: Renamed the third key from `message` to
`exc_message`. The D-027 three-key **mandate** (and the
ordering of the keys: cid / type / message-content) is
preserved; only the canonical name changed. Recorded in
`MEMORY.md`, `CURRENT_STATE.md`, `NEXT_AGENT.md`, and
`docs/AUDITS/M3_REPORT.md`.

**Resolved**: 2026-06-20. Part of M3 closure commit `fb110bd`.

## F-30 - Starlette `ServerErrorMiddleware` re-raises after handler

**Tag**: MEDIUM (architectural drift; framework-level)
**Location**: `starlette.middleware.errors.ServerErrorMiddleware`
(starlette 0.48, vendored via FastAPI 0.116.2).

**Finding**: M3's first-pass catch-all used
`FastAPI.add_exception_handler(Exception, ...)`. Starlette's
outer `ServerErrorMiddleware` accepts the handler and writes
its response, then unconditionally `raise exc` at the end of
`__call__`. `httpx.ASGITransport` then re-raises the
exception to the client test, breaking the
`test_unhandled_exception_returns_envelope` assertion even
though the response had been sent.

**Fix**: M3 installs the catch-all as a
`BaseHTTPMiddleware` (`_ErrorEnvelopeMiddleware`) that
consumes the exception inside the request pipeline. The
response is returned from `dispatch`; the framework's
outer re-raise becomes harmless because the response is
already committed. Future domain-error handlers layer on
top of this middleware in a future milestone.

**Resolved**: 2026-06-20. Part of M3 closure commit `fb110bd`.

---

## Summary

- Critical: 1 (F-21)
- High: 10 (F-1, F-3, F-5, F-8 [doc-side], F-14 [doc-side], F-22, F-23, F-24, F-25, F-27)
- Medium: 10 (F-2, F-7, F-9, F-11, F-17, F-20, F-26, F-28, F-29, F-30)
- Low: 9

The critical finding (F-21) was discovered during developer-side
verification, not during the original engineering pass. It is
addressed in a follow-up commit that also updates the audit
follow-up row.

F-22 was discovered during the F-21 re-verification pass. The fix
is a single-file change to the compose healthcheck quoting.

F-23 was discovered during the F-22 re-verification pass. The fix
is a single-line change to the compose port mapping.

The high-severity portability and schema-correctness findings
(F-1, F-3, F-5, F-17) will be fixed in this remediation pass.
The remaining items are documented for their owning milestones
or accepted as-is.

---

## F-31 — M5 auth middleware: dispatcher methods reference unbound `verify_jwt`

**Tag**: MEDIUM (architectural drift; symptom-level 500)
**Location**: `src/api/middleware/auth.py`. The initial
`JwtAuthMiddleware` had `_dispatch_token` and `_dispatch_failure`
methods that referenced a bare `verify_jwt` name. The local
`verify_jwt` lookup inside `__call__` only existed in `__call__`'s
local scope; the dispatcher methods (instance methods, not
nested functions) did not see it. Calling the middleware on any
non-skip path raised `NameError: name 'verify_jwt' is not defined`,
which the M3 catch-all middleware turned into a 500 envelope. The
5-test failure pattern during initial M5 verification — every
test that hit the middleware except the pure-skip paths — was the
clear signature of the bug.

**Fix**: pass `verify_jwt` as an explicit keyword argument from
`__call__` to `_dispatch_token` and `_dispatch_failure`. Each
dispatcher now receives its single collaborator as a typed
parameter; no closure ambiguity. 6/6 middleware tests green;
combined pytest 73/73 green.

**Resolved**: 2026-06-21. Part of the M5 closure commit.

## F-32 — M5 test route: FastAPI treats bare `request` as a query param

**Tag**: LOW (test-only ergonomics)
**Location**: `tests/api/test_auth_middleware.py`. The test
ephemeral `/protected` route declared `async def _echo_actor(request)`
without a `Request` type annotation. FastAPI's parameter binding
step interpreted `request` as a query parameter and produced
HTTP 422 on every successful-verification call, masking the
real auth middleware path.

**Fix**: change `async def _echo_actor(request):` to
`async def _echo_actor(request: Request):`. `Request` is the
canonical FastAPI-Starlette type for the framework-injected
request object. The route now succeeds at 200 with a valid
token and 401 with a missing / bad-signature token.

**Resolved**: 2026-06-21. Part of the M5 closure commit.

## F-33 — Test HS256 secrets below PyJWT's 32-byte minimum

**Tag**: LOW (cosmetic; warning-level diagnostics)
**Location**: `tests/api/conftest.py`,
`tests/application/auth/conftest.py`,
`tests/application/auth/test_hs256_signer.py`,
`tests/api/test_auth_middleware.py`. Several fixture-level
and inline `tests/application/auth/test_hs256_signer.py`
secrets were below PyJWT's 32-byte recommended key length.
PyJWT emitted `InsecureKeyLengthWarning` on every
`encode` / `decode` call.

**Fix**: bump fixture constants to ≥32 bytes:
`b"dev-secret-for-tests-with-32-byte-min-len!"`,
`b"test-secret-do-not-use-in-prod-32-bytes!"`,
`b"another-secret-not-the-real-one-32b!"`,
`b"different-secret-than-the-real-one!"`. PyJWT warning
silenced; all assertions still hold (length is well above
the HS256 minimum).

**Resolved**: 2026-06-21. Part of the M5 closure commit.

## F-34 — M5 middleware reads auth state via `scope["app"].state`, not `self._app`

**Tag**: LOW (architectural hygiene)
**Location**: `src/api/middleware/auth.py`. The middleware
runtime resolution of `app.state.verify_jwt` was originally
typed as `getattr(self._app.state, "verify_jwt", None)`.
`self._app` is the **inner** wrapped application (the
next-layer middleware or the FastAPI routing), not the
FastAPI host application. Starlette injects the FastAPI
host application at `scope["app"]`, so the correct lookup
is `scope.get("app")` then `getattr(fastapi_app.state,
"verify_jwt", None)`.

**Fix**: rewrite the lookup explicitly. The middleware is
still a pure-ASGI class with `self._app` as its
forwarder; the runtime state read is per-request through
`scope["app"]`. This mirrors the pattern used by the M3
correlation middleware. 6/6 middleware tests green.

**Resolved**: 2026-06-21. Part of the M5 closure commit.

---

## Summary (updated through M7)

- Critical: 1 (F-21)
- High: 10 (F-1, F-3, F-5, F-8 [doc-side], F-14 [doc-side], F-22, F-23, F-24, F-25, F-27)
- Medium: 11 (F-2, F-7, F-9, F-11, F-17, F-20, F-26, F-28, F-29, F-30, F-31)
- Low: 17 (F-4, F-6, F-10, F-12, F-13, F-15, F-16, F-18, F-19, F-32, F-33, F-34, F-35, F-36, F-37, F-38, F-29-of-32)

M5 surfaced four new findings (F-31..F-34). F-31 was the most
significant: a `NameError`-of-deceiving-shape that produced 500s
on every non-skip request during initial verification. F-32..F-34
were self-contained test/wiring-hygiene items.

M6 surfaced one new finding (F-35): the langgraph channel-shape
versus typed-state split is intentional (framework-side mutable
versus application-side immutable contract), not drift. F-35 is
accepted at the LOW level and documented in
`docs/AUDITS/M6_REPORT.md`.

M7 surfaced three new findings (F-36, F-37, F-38). All three are
documented in `docs/AUDITS/M7_REPORT.md` and accepted at the
LOW level:

  - F-36 — the deterministic-hash embedding stub is a placeholder
    pending the Embedding Model capability (open question D-002);
    production-shaped embeddings land at the milestone that adopts
    the capability.
  - F-37 — the M7 reason-code widening lives in the
    `_ALLOWED_REASON_CODES` predicate, NOT in the `ReasonCode`
    Literal; the literal stays narrowed to the seven M0 codes
    (D-044 carried forward).
  - F-38 — the typed-error slug defaults to `"ingestion_failed"`
    on the base exception; each subclass overrides the slug so the
    audit row's `metadata["error_code"]` carries a stable
    app-domain-side identifier.

---

## F-35 — M6 Channel-shape vs. typed-state mismatch is intentional, not architectural drift

**Tag**: LOW (architectural hygiene; documented)
**Location**: `src/infrastructure/langgraph/workflow.py`
(`_WorkflowChannel` declaration) versus
`src/application/workflow/state.py` (`WorkflowState`).

**Finding**: The langgraph framework expects the
`StateGraph` channel to be a `TypedDict` with `total=False` for
the framework's state-diff machinery. The application package
declares `WorkflowState` as a frozen dataclass with required
(non-blankable) fields. The two layers are intentionally not
collapsed: the channel is framework-side, mutable, and
intermediate-traversal-friendly; the dataclass is application-
side, immutable, and contract-binding.

If `WorkflowState` were itself a `TypedDict`, the M6 typed
contract would lose its `__post_init__`
`IncompleteActorError` enforcement. If `_WorkflowChannel`
were `total=True`, the graph would refuse every legitimate
partial update during traversal.

**Status**: Accepted-Low. Documented in `docs/AUDITS/M6_REPORT.md`
under "Architectural drift discovered (none new)" and
"Findings raised during M6 (F-35)". The two layers cooperate
through `build_initial_channel` (typed -> channel) and
`from_state_dict` (channel -> typed), with the channel
projection rebuilt into a typed `WorkflowState` and the typed
state's `__post_init__` running again at reconstruction time.

**No change planned**. The architectural invariant — the
application package stays framework-free; the infrastructure
layer owns the framework binding — is preserved and exercised
by 13 M6 tests.

---

## F-36 -- M7 embedding stub ships as placeholder pending the Embedding Model capability

**Tag**: LOW (capability-deferred; documented)
**Location**: src/infrastructure/ingestion/embedding.py (DeterministicHashEmbeddingModel).

**Finding**: M7 ships a deterministic-hash embedding stub as the canonical implementation of the V1 EmbeddingModelProtocol. The stub produces a reproducible 1536-dim vector from any input text via per-dimension sha256. The capability is intentionally not pinned at M7 -- the Embedding Model capability is open question D-002; the embedding SDK lands at the milestone that adopts the capability (a future M8 / M11 milestone per PROJECT_STATUS.md).

**Status**: Accepted-Low. Documented in docs/AUDITS/M7_REPORT.md under Findings raised during M7 (F-36). The stub is capability-shaped; production wiring (i.e. the future __main__ / runtime hook) swaps the constructor inside the application module's runtime wiring without touching the application package. The application use case IngestDocument imports the protocol only; capability swapping is local to the adapter layer.

**No change planned at M7**. Capability adoption is open question D-002 and is owned by a future milestone.

---

## F-37 -- M7 reason-code widening in the predicate, not the Literal (D-044 carried forward)

**Tag**: LOW (architectural hygiene; documented)
**Location**: src/domain/ports/reason_codes.py (_ALLOWED_REASON_CODES).

**Finding**: M7 extends the V1-allowed reason-codes set with three ingestion outcome codes (ingestion_succeeded, ingestion_skipped, ingestion_failed). The strict ReasonCode Literal stays narrowed to the seven M0 codes because the access-decision pure function's output shape is preserved. The widening lives in _ALLOWED_REASON_CODES: frozenset[str] and is queried via is_allowed_reason_code(value), which the audit-log repository enforces at append time.

**Status**: Accepted-Low. Documented in docs/AUDITS/M7_REPORT.md under Findings raised during M7 (F-37). The M5/D-044 rule (ReasonCode Literal stays narrow; predicate accumulates new V1 codes) is preserved and exercised by the M7 ingestion use-case tests, which assert that the audit rows land with eason_code in {ingestion_succeeded, ingestion_skipped, ingestion_failed}.

**No change planned**. New V1 codes continue to extend the predicate, not the literal.

---

## F-38 -- M7 IngestionDomainError.code defaults to ingestion_failed so each subclass can override the slug

**Tag**: LOW (typed-error hygiene; documented)
**Location**: src/application/ingestion/errors.py.

**Finding**: The base IngestionDomainError exception carries a class attribute code: str = ingestion_failed`. Every concrete subclass (IngestionPipelineError, MissingContentError, EmbeddingShapeMismatchError) overrides the slug so the audit row's metadata[error_code] carries a stable, fine-grained id without the application code knowing about exception-subtype switches. The use case's _emit_failure_audit line writes metadata[error_code] = exc.code directly; tests assert on the slug (e.g. embedding_shape_mismatch) rather than on the message text. This is the same pattern the M5 auth package uses for JwtMissing / JwtMalformed / etc. -- class-attribute slugs are stable identifiers that ride across translation.

**Status**: Accepted-Low. Documented in docs/AUDITS/M7_REPORT.md under Findings raised during M7 (F-38). The pattern is intentionally consistent with the M5 auth-error hierarchy: typed-failure slugs are the canonical audit-row identifiers at every future boundary (/v1/... ingest / /v1/... query).

**No change planned**.


## F-39 -- M8 in-memory dense + BM25 algorithm parity with ParadeDB defaults

**Tag**: LOW (capability parity; documented)
**Location**: src/infrastructure/retrieval/in_memory_dense.py, src/infrastructure/retrieval/in_memory_bm25.py.

**Finding**: The V1 in-memory dense retriever scans the in-memory catalog with cosine similarity. The V1 in-memory BM25 retriever uses k1=1.5, b=0.75 (ParadeDB / pg_search defaults). Both adapters honor the typed AccessPolicyFilter projection the same way the future pgvector / pg_search SQL adapters must, so the dense / BM25 candidate sets stay aligned. The cosine + BM25 implementations are pure Python and locked at these hyperparameter values so the SQL adoption is a direct translation with no algorithmic drift.

**Status**: Accepted-Low. Documented in docs/AUDITS/M8_REPORT.md under Findings raised during M8 (F-39). The pgvector / pg_search SQL adoption is the M12+ milestone; the algorithm parity de-risks that swap.

## F-40 -- M8 RetrievalCandidate rebuild to attach document_projection for observability

**Tag**: LOW (in-orchestrator allocation cost; documented)
**Location**: src/application/retrieval/retrieve.py.

**Finding**: The post-rerank drop re-builds RetrievalCandidate to attach the resolved document_projection so observability rows and downstream boundaries can read it without a documents-port round-trip. RetrievalCandidate is a frozen dataclass so the rebuild is a fresh allocation per survivor. The cost is negligible at top_n <= 8 (the M9 production cap); a hot-path optimization (mutating the candidate or caching the projection) lands at the framework-adapter or future SQL coercion layer. The current cost is observed by the M8 application tests; no M8 benchmark regression is recorded.

**Status**: Accepted-Low. Documented in docs/AUDITS/M8_REPORT.md under Findings raised during M8 (F-40). No change planned at M8; the optimization lives outside the application boundary.
