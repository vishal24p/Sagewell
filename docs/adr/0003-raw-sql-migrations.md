# ADR-0003: Migrations Are Raw Numbered SQL Pairs

**Date**: 2026-06-19
**Status**: accepted
**Deciders**: Project maintainers

## Context

M1 requires reversible migrations. The project has no migration
tool named in any source-of-truth document. Candidate tools
considered: raw SQL migration pairs (apply and rollback files),
Alembic (Python), `dbmate`, `yoyo-migrations`, `sqitch`.

V1's `DATABASE_SCHEMA.md` is PostgreSQL-first with explicit
column types, indexes, and constraints. Adding a Python ORM or
schema-builder between the SQL narrative and the actual schema
adds an indirection that must be kept in lock-step with the
narrative. The architecture narrative itself (`ARCHITECTURE.md`)
calls Postgres the data store and lists the components that read
from it; nothing in that narrative selects a Python ORM or a
schema DSL.

## Decision

Migrations live as raw numbered SQL pairs on disk:

```
migrations/
  001_extensions.up.sql
  001_extensions.down.sql
  002_schema.up.sql
  002_schema.down.sql
  003_indexes.up.sql
  003_indexes.down.sql
  004_fixtures.up.sql
  004_fixtures.down.sql
```

The migration execution tooling lives in Python under
`infrastructure/migrations/`. The apply and rollback scripts
shell out to `psql` from the project database URL with each
file in order. Idempotency is enforced by the SQL itself
(`CREATE EXTENSION IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`,
`DROP TABLE IF EXISTS`).

No Alembic, SQLAlchemy, `dbmate`, `yoyo-migrations`, or `sqitch`
is adopted.

Fixtures are SQL files referenced by `004_fixtures*.sql`, living
under `db/fixtures/`. The fixture `up.sql` reads them; the
fixture `down.sql` removes them.

## Alternatives Considered

### Alternative 1: Alembic

- **Pros**: Python-native, integrates with the project pyproject,
  autogenerate from SQLAlchemy models.
- **Cons**: Requires SQLAlchemy models for autogeneration; the
  project does not use SQLAlchemy. Hand-written Alembic
  migrations collapse to raw SQL anyway, with extra Python
  plumbing.
- **Why not**: Adds ORM-style complexity with no payoff at the
  schema milestone; the project does not adopt SQLAlchemy.

### Alternative 2: `dbmate`

- **Pros**: Declarative SQL with `up/down` files; small CLI.
- **Cons**: External CLI dependency, versioned separately; the
  schema milestone should be reproducible without bootstrapping
  a third binary.
- **Why not**: Adds a Rust-binary dependency for what is a
  numbers-in-order and a per-file `psql` invocation.

### Alternative 3: `yoyo-migrations`

- **Pros**: Python, lightweight, uses SQL files.
- **Cons**: Adds a Python package and a runner concept; the
  internal `infrastructure/migrations/` runner is simpler and
  more obviously auditable.
- **Why not**: Same as `dbmate`. Auditable simplicity wins at
  M1.

### Alternative 4: `sqitch`

- **Pros**: Pure-SQL, deployment-tag-based, strong rollback.
- **Cons**: Adds a Perl-based toolchain; V1 has no other Perl
  dependency, so this is the largest runtime surface area of
  the four candidates.
- **Why not**: Same.

## Consequences

### Positive

- The schema milestone's source of truth is plain SQL, the
  same language `DATABASE_SCHEMA.md` narrates in.
- `infrastructure/migrations/apply.sh` and `rollback.sh` are
  short shell scripts. Both readable and auditable.
- No additional language or binary is added to the toolchain.
- The reversal of any single migration is co-located with the
  migration itself in the same numeric slot.

### Negative

- The apply and rollback runners implement ordering and
  idempotency discipline manually. Migrations must avoid
  partial-application states.
- Without autogenerate, schema narration drift between
  `DATABASE_SCHEMA.md` and the migration SQL is detectable
  only by review.

### Risks

- A migration can be applied in the up direction but a forgotten
  down file makes rollback incomplete. Mitigation: each up SQL
  ships with a paired down SQL on day one; release gate refuses
  a missing down file.
- Manual ordering mistakes. Mitigation: numeric prefixes and
  monotonicity are visible at a glance. The apply runner reads
  them sorted.
