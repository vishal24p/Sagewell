# M1 Verification Report

**Date**: 2026-06-19
**Status**: PASSED
**Target**: `docs/AUDITS/M1_VERIFICATION_REPORT.md`

This report is the developer-side log of M1 verification.
**Status is now PASSED.** Status moves from PENDING LOCAL
EXECUTION to PASSED once the developer records every step in
the procedure below as Pass. Steps A through I ran clean
against the corrected image tag (`paradedb/paradedb:pg17`),
the corrected healthcheck (`echo ... | psql -tAX | grep -q
'^1$'`), and the corrected dev compose host port (55432).

The reporting developer runs the procedure in order. Each step's
outcome is recorded in the table under "Results". A line in
"Findings" records any defect encountered.

---

## Procedure (Run In Order)

### A. Bring up Postgres plus pg_search

```bash
docker compose -f docker/compose.dev.yml up -d
```

Wait for the healthcheck to report pg_search is present:

```bash
docker compose -f docker/compose.dev.yml ps
```

Document the host and port. The dev compose publishes the
container port on host **55432** (NOT 5432) to avoid a collision
with the Windows-native Postgres service that commonly binds 5432
on developer machines. The same Postgres image is not the host
service: a host psql session on `localhost:5432` lands on the
wrong Postgres and produces a `password authentication failed`
error even though the container's Postgres is correct. See
`docs/AUDITS/FINDINGS.md` F-23.

A developer without that host-side collision can resolve the
container via `localhost:55432` directly, or temporarily
override the port mapping by exporting `COMPOSE_PORT_HOST=5432`
before `docker compose up -d` (see compose header comments).

### B. Apply migrations

Set the `SAGEWELL_DB_URL` environment variable to a local
connection URL. Then run the apply script from the repo root.

```bash
./infrastructure/migrations/apply.sh
```

Expected output: every up migration file prints `[apply] ...`
and ends with `[apply] done`.

### C. Verify tables

```bash
psql "$SAGEWELL_DB_URL" -c '\dt'
```

Expected output: six V1 tables named users, documents, chunks,
audit_logs, retrieval_logs, evaluation_results.

### D. Verify extensions

```bash
psql "$SAGEWELL_DB_URL" -c "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_search');"
```

Expected output: both rows present.

### E. Verify indexes

```bash
psql "$SAGEWELL_DB_URL" -c '\di'
```

Expected output: four indexes — chunks_document_id_idx,
chunks_status_idx, documents_access_filter_idx,
chunks_embedding_idx.

### F. Verify fixtures loaded

```bash
psql "$SAGEWELL_DB_URL" -c "SELECT count(*) FROM users;"
psql "$SAGEWELL_DB_URL" -c "SELECT count(*) FROM documents;"
psql "$SAGEWELL_DB_URL" -c "SELECT count(*) FROM chunks;"
```

Expected outputs: at least 10 fixture users, at least 10
fixture documents, at least 10 fixture chunks.

### G. EXPLAIN check for access filter index

```bash
psql "$SAGEWELL_DB_URL" -c "EXPLAIN SELECT * FROM documents WHERE department='finance' AND required_clearance='INTERNAL' AND status='active';"
```

Expected: a planned path that uses documents_access_filter_idx
or a sequential scan if the planner judges the row count too
small to benefit. Either is acceptable; if a sequential scan is
chosen, run the same query with ANALYZE against a seed of at
least 1000 rows (`INSERT INTO documents ... SELECT ... FROM
generate_series(1,1000)` then `ANALYZE documents`) and re-EXPLAIN.

### H. Round-trip: rollback, re-apply

```bash
export SAGEWELL_ROLLBACK_CONFIRM=I_UNDERSTAND
./infrastructure/migrations/rollback.sh
```

Expected: every down migration runs and exits 0.

```bash
./infrastructure/migrations/apply.sh
```

Expected: every up migration runs and exits 0.

### I. Re-verify

Re-run steps C-F. All six tables, two extensions, four indexes,
and the fixture counts must still be present.

---

## Results

| Step | Command | Expected | Actual | Pass / Fail |
|---|---|---|---|---|
| A | docker compose up -d | Postgres + pg_search ready | dev container started; healthcheck green post-F-22 fix; F-21 image tag in place; F-23 port mapping active | Pass |
| B | apply.sh | All migrations apply | migrations 001-004 applied cleanly against `localhost:55432` | Pass |
| C | `\dt` | 6 V1 tables | users, documents, chunks, audit_logs, retrieval_logs, evaluation_results | Pass |
| D | extension query | vector + pg_search | both rows visible via `psql` | Pass |
| E | `\di` | 4 indexes | chunks_document_id_idx, chunks_status_idx, documents_access_filter_idx, chunks_embedding_idx | Pass |
| F | fixture counts | >=10 users / docs / chunks | 10 fixture users / docs / chunks loaded from `db/fixtures/*.sql` | Pass |
| G | EXPLAIN | uses access filter index (or sequential with justification) | `documents_access_filter_idx` selected by the planner | Pass |
| H-I | rollback + apply | clean round-trip | `SAGEWELL_ROLLBACK_CONFIRM=I_UNDERSTAND ./infrastructure/migrations/rollback.sh` followed by `./infrastructure/migrations/apply.sh` re-applied all four up files; final state matches the post-step-B state | Pass |## Findings

### F-21 Plus F-22 (discovered during re-verification of Step A)

After F-21 (`docker.io/paradedb/paradedb:stable: not found`) was
corrected to `paradedb/paradedb:pg17` (commit `dc21743`), the dev
container started successfully and the database plus extensions
were present and valid. The Compose healthcheck, however, failed
in a non-healthy loop because the YAML single-quoted scalar in
the healthcheck collided with the inner SQL single-quote escape
("shell quoting inside Compose quoting"). This was caught by the
developer-side verification, not by the engineering pass.

F-22 (`docs/AUDITS/FINDINGS.md`) corrected the healthcheck by
reflowing the SQL probe to `echo ... | psql -tAX | grep -q '^1$'`.
That change is Compose-yaml-only; no schema, migration, or ADR
changes were required.

Step A outcome re-evaluates to PASS once the developer records the
post-F-22 outcome in the results table above.

### F-23 (host port collision)

After F-21 and F-22 landed, the in-container `psql` succeeded but
host `psql ...@localhost:5432` failed with
`password authentication failed for user "sagewell"`. Diagnostic
PowerShell commands revealed `postgres.exe` (PID 5444) and Docker
Desktop's `com.docker.backend.exe` (PID 13400) both listening on
5432; Windows routed the host's psql session to the host-resident
listener rather than the dev container. F-23 remapped the dev
compose's host-published port from 5432 to 55432. Architecture
remains "Postgres in Docker, apply.sh via host psql". The role
namespace and the `apply.sh` script are unchanged; the developer
points `SAGEWELL_DB_URL` at `localhost:55432`.

Resolution: PASS. Steps B onward ran clean after the F-23 fix.

## Conclusion

The status remains PASSED once the developer records
Pass / Fail for every step above. Once all Pass, this file is
updated to status PASSED with the recorded outcomes in the table
above. Status flipped to PASSED on 2026-06-19 after the developer
ran the full procedure against the corrected dev compose.

Status: **PASSED**.
