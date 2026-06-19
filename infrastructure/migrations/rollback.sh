#!/usr/bin/env bash
# infrastructure/migrations/rollback.sh
#
# Rollback migrations in REVERSE numbered order using psql.
# Refuses to run unless SAGEWELL_ROLLBACK_CONFIRM=I_UNDERSTAND
# is set in the environment. This is a destructive operation.
#
# Required environment:
#   SAGEWELL_DB_URL            -- psql-style connection URL
#   SAGEWELL_ROLLBACK_CONFIRM  -- must be set to I_UNDERSTAND
#
# Optional environment:
#   SAGEWELL_MIGRATIONS_DIR    -- absolute path to migrations/
#                                  (default: <repo>/migrations)

set -euo pipefail

: "${SAGEWELL_DB_URL:?SAGEWELL_DB_URL must be set to a psql-style connection URL}"
: "${SAGEWELL_ROLLBACK_CONFIRM:?SAGEWELL_ROLLBACK_CONFIRM must be set to I_UNDERSTAND before rollback proceeds (see M1 finding F-7)}"

if [ "$SAGEWELL_ROLLBACK_CONFIRM" != "I_UNDERSTAND" ]; then
    echo "[rollback] FATAL: SAGEWELL_ROLLBACK_CONFIRM is set but is not 'I_UNDERSTAND'." >&2
    exit 1
fi

command -v psql >/dev/null 2>&1 || {
    echo "[rollback] FATAL: \`psql\` not found on PATH. Install PostgreSQL client tools first." >&2
    exit 1
}

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MIG_DIR="${SAGEWELL_MIGRATIONS_DIR:-$REPO_ROOT/migrations}"

if [ ! -d "$MIG_DIR" ]; then
    echo "[rollback] FATAL: migrations directory not found at $MIG_DIR" >&2
    exit 1
fi

echo "[rollback] migrations=$MIG_DIR"
echo "[rollback] WARNING: every down file will now be applied to $SAGEWELL_DB_URL"

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

# Reminder: rollback on a shared database destroys ALL rows for
# every V1 table. Run only against dev DBs. See rollback safety
# notes in docs/AUDITS/FINDINGS.md F-7.
echo "[rollback] done -- reverse-order down files applied."
