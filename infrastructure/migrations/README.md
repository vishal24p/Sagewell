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

Set `SAGEWELL_DB_URL` to your local connection URL. The runner
uses the canonical migrations tree. Run:

```bash
./infrastructure/migrations/apply.sh
```

The apply script sets the SQL variable `:fixtures_dir` to the
absolute path of `db/fixtures/` so the fixture migration's `\i`
references resolve at runtime (portable across developer machines;
see `docs/AUDITS/FINDINGS.md` F-5).

## Rollback

Rollback is **destructive**. It walks down files in reverse
numeric order, one per transaction. Use only on a dev DB you
are willing to wipe.

```bash
export SAGEWELL_ROLLBACK_CONFIRM=I_UNDERSTAND
./infrastructure/migrations/rollback.sh
```

The runner refuses to proceed without the explicit confirmation
env var. See `docs/AUDITS/FINDINGS.md` F-7.

## Verification (developer side)

The full developer-side verification procedure is in
`docs/AUDITS/M1_VERIFICATION_REPORT.md`. The procedure covers
compose up, apply, table and extension list, index list,
fixture counts, EXPLAIN check, rollback, and re-apply.

## Sandbox Note

Authoring the files does not run any of the verification commands;
verification is a developer-side step. **M1 must not be marked
Closed** in `docs/HANDOFF/CURRENT_STATE.md` until the verification
report shows status `PASSED`.

Other required reading before marking M1 verified:

- `docs/AUDITS/FINDINGS.md` — engineering findings.
- `docs/AUDITS/M1_REMEDIATION_REPORT.md` — re-audit after fixes.
- `docs/AUDITS/MIGRATION_CHECKLIST.md` — gate checks the reviewer
  applied during the engineering pass.
