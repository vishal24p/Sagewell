# infrastructure/migrations/

Apply and rollback V1 Postgres migrations under `migrations/`.

The scripts shell out to `psql`. They do not introduce ORM
dependencies (per ADR-0003). They are auditable, short, and
require only `bash` and `psql`.

## Prerequisites

- `psql` is on the PATH.
- A Postgres instance is reachable from the environment. Set the
  `SAGEWELL_DB_URL` environment variable to the connection URL
  appropriate for your environment.

For local development use the Docker compose defined at
`docker/compose.dev.yml`:

```powershell
docker compose -f docker/compose.dev.yml up -d
```

That compose ships a Postgres-based image with the ParadeDB
`pg_search` extension pre-installed. Wait for the healthcheck
to report `pg_search` is present.

## Apply

Set `SAGEWELL_DB_URL` to your local connection string (the
dev defaults in `docker/compose.dev.yml` are documented inline;
production deployments must source the URL from a secret
manager), then run:

```bash
./infrastructure/migrations/apply.sh
```

## Rollback

Rollback runs the down files in reverse numeric order, one per
transaction. Use only if you intend to take the database back
to the pre-migration state.

```bash
./infrastructure/migrations/rollback.sh
```

## Verification (developer side)

After a clean apply, the following confirm the schema is correct.

```bash
psql "$SAGEWELL_DB_URL" -c '\dt'
psql "$SAGEWELL_DB_URL" -c '\di'
psql "$SAGEWELL_DB_URL" -c "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_search');"
psql "$SAGEWELL_DB_URL" -c "SELECT count(*) FROM users;"
psql "$SAGEWELL_DB_URL" -c "SELECT count(*) FROM documents;"
psql "$SAGEWELL_DB_URL" -c "SELECT count(*) FROM chunks;"

# EXPLAIN check for documents_access_filter_idx:
psql "$SAGEWELL_DB_URL" -c "EXPLAIN SELECT * FROM documents WHERE department='finance' AND required_clearance='INTERNAL' AND status='active';"
```

Then rollback and re-apply to confirm reversibility:

```bash
./infrastructure/migrations/rollback.sh
./infrastructure/migrations/apply.sh
```

## Sandbox Note

These verification steps require a Postgres reachable from the
running environment. Authoring the files does not run any of
them; verification is a developer-side step. M1 will not be
claimed verified in the handoff until these commands have run
end-to-end.
