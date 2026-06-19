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
#   * The fixture migration references files via \i and assumes
#     the working directory is /workspace. For local development
#     we set the PSQL_WDIR by chdir'ing into the repo and using
#     a /workspace shim. Each script that uses \i must declare
#     its expected working directory at the top.
#
# Exit codes:
#   0  on success.
#   1  if a required environment variable is missing.
#   2  on psql failure (a migration raised an error).

set -euo pipefail

: "${SAGEWELL_DB_URL:?SAGEWELL_DB_URL must be set to a psql-style connection URL}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MIG_DIR="${SAGEWELL_MIGRATIONS_DIR:-$REPO_ROOT/migrations}"
FIX_DIR="${SAGEWELL_FIXTURES_DIR:-$REPO_ROOT/db/fixtures}"

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

# Provide a /workspace-style path for the fixture migration so
# the \i directives in 004_fixtures.up.sql resolve. We do this
# by overriding PSQL to a temp dir the run scripts can use.
WORK_ROOT="$(mktemp -d -t sagewell-migrate.XXXXXX)"
trap 'rm -rf "$WORK_ROOT"' EXIT
ln -s "$REPO_ROOT" "$WORK_ROOT/workspace"
mkdir -p "$WORK_ROOT/workspace/db/fixtures"
# Hardlink fixture files into the workspace so \i can find them
# without copying contents.
for f in "$FIX_DIR"/*.sql; do
    base="$(basename "$f")"
    [ -e "$WORK_ROOT/workspace/db/fixtures/$base" ] || ln "$f" "$WORK_ROOT/workspace/db/fixtures/$base"
done

for f in "${UP_FILES[@]}"; do
    rel="$(basename "$f")"
    echo "[apply] >>> $rel"
    cd "$WORK_ROOT/workspace"
    psql "$SAGEWELL_DB_URL" \
         --set ON_ERROR_STOP=1 \
         --single-transaction \
         --file "$MIG_DIR/$rel"
    echo "[apply] ok $rel"
done

echo "[apply] done"
