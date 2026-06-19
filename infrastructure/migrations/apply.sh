#!/usr/bin/env bash
# infrastructure/migrations/apply.sh
#
# Apply V1 migrations in numbered order using psql.
#
# Required environment:
#   SAGEWELL_DB_URL  -- psql-style connection URL for the target
#                       Postgres database. Set this at runtime.
#
# Optional environment:
#   SAGEWELL_MIGRATIONS_DIR -- absolute path to migrations/
#                              (default: <repo>/migrations)
#   SAGEWELL_FIXTURES_DIR   -- absolute path to db/fixtures/
#                              (default: <repo>/db/fixtures)
#
# Behavior:
#   * Reads every NNN_*.up.sql file under $SAGEWELL_MIGRATIONS_DIR
#     in sorted order.
#   * Calls psql once per file with --single-transaction so each
#     migration is atomic. The migration files themselves are
#     idempotent (CREATE EXTENSION IF NOT EXISTS, CREATE TABLE IF
#     NOT EXISTS, CREATE INDEX IF NOT EXISTS).
#   * Passes :fixtures_dir as a psql SQL variable so the fixture
#     migration's \\i references resolve at runtime instead of
#     hard-coding /workspace. See M1 finding F-5.
#   * Requires `psql` on PATH and refuses to run if it is missing.
#
# Exit codes:
#   0  on success.
#   1  if a required environment variable or tool is missing.
#   2  on psql failure (a migration raised an error).

set -euo pipefail

: "${SAGEWELL_DB_URL:?SAGEWELL_DB_URL must be set to a psql-style connection URL}"

command -v psql >/dev/null 2>&1 || {
    echo "[apply] FATAL: \`psql\` not found on PATH. Install PostgreSQL client tools first." >&2
    exit 1
}

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MIG_DIR="${SAGEWELL_MIGRATIONS_DIR:-$REPO_ROOT/migrations}"
FIX_DIR="${SAGEWELL_FIXTURES_DIR:-$REPO_ROOT/db/fixtures}"

if [ ! -d "$MIG_DIR" ]; then
    echo "[apply] FATAL: migrations directory not found at $MIG_DIR" >&2
    exit 1
fi
if [ ! -d "$FIX_DIR" ]; then
    echo "[apply] FATAL: fixtures directory not found at $FIX_DIR" >&2
    exit 1
fi

echo "[apply] repo=$REPO_ROOT migrations=$MIG_DIR fixtures=$FIX_DIR"
echo "[apply] db=(set via SAGEWELL_DB_URL)"

# POSIX sort + numeric ordering is sufficient for NNN_*.up.sql.
shopt -s nullglob
UP_FILES=( "$MIG_DIR"/[0-9][0-9][0-9]_*.up.sql )
shopt -u nullglob

if [ ${#UP_FILES[@]} -eq 0 ]; then
    echo "[apply] no migrations found in $MIG_DIR" >&2
    exit 1
fi

for f in "${UP_FILES[@]}"; do
    rel="$(basename "$f")"
    echo "[apply] >>> $rel"
    psql "$SAGEWELL_DB_URL" \
         --set ON_ERROR_STOP=1 \
         --single-transaction \
         --set "fixtures_dir=$FIX_DIR" \
         --file "$f"
    echo "[apply] ok $rel"
done

echo "[apply] done"
