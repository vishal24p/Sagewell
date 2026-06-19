#!/usr/bin/env bash
# infrastructure/migrations/rollback.sh
#
# Rollback migrations in REVERSE numbered order using psql.
# Treats every down file as reversible; each down SQL is
# responsible for its own idempotency.
#
# Required environment:
#   SAGEWELL_DB_URL  -- psql-style connection URL for the target
#                       Postgres database. Set this at runtime.
#
# Optional environment:
#   SAGEWELL_MIGRATIONS_DIR -- absolute path to migrations/
#                              (default: <repo>/migrations)

set -euo pipefail

: "${SAGEWELL_DB_URL:?SAGEWELL_DB_URL must be set to a psql-style connection URL}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MIG_DIR="${SAGEWELL_MIGRATIONS_DIR:-$REPO_ROOT/migrations}"

echo "[rollback] migrations=$MIG_DIR"

shopt -s nullglob
DOWN_FILES=( "$MIG_DIR"/[0-9][0-9][0-9]_*.down.sql )
shopt -u nullglob

if [ ${#DOWN_FILES[@]} -eq 0 ]; then
    echo "[rollback] no migrations found in $MIG_DIR" >&2
    exit 1
fi

# Apply down files in reverse order.
for (( i=${#DOWN_FILES[@]}-1; i>=0; i-- )); do
    f="${DOWN_FILES[$i]}"
    rel="$(basename "$f")"
    echo "[rollback] <<< $rel"
    psql "$SAGEWELL_DB_URL" \
         --set ON_ERROR_STOP=1 \
         --single-transaction \
         --file "$f"
    echo "[rollback] ok $rel"
done

echo "[rollback] done"
