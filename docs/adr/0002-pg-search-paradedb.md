# ADR-0002: pg_search Implementation Is ParadeDB

**Date**: 2026-06-19
**Status**: accepted
**Deciders**: Project maintainers
**Closes**: `docs/HANDOFF/KNOWN_ISSUES.md` I-004

## Context

V1 retrieval requires BM25 lexical search via `pg_search`. The
specific distribution and version are not pinned and `KNOWN_ISSUES.md`
marks this as a blocker for M1 (schema, migrations, indexes).

Two competing candidates exist:

- ParadeDB `pg_search` (most actively developed PostgreSQL-based
  distribution; ships inside a Postgres-based Docker image; supports
  BM25 inverted indexes and a `text_search` column convention).
- Older `pg_search` named extensions historically shipped by other
  vendors and PostgreSQL contrib's `tsvector` plus GIN indexes.

V1 retrieval also depends on `pgvector`. The chosen bundle must
provide both extensions, ideally from a single image, so M1 can
create both extensions without per-extension version juggling.

## Decision

Sagewell V1 uses **ParadeDB `pg_search`** for the lexical retrieval
path. The schema migration creates the extension with
`CREATE EXTENSION IF NOT EXISTS pg_search`. The lexical index on
`chunks.text_search` and any associated BM25 query syntax follow
the ParadeDB pg_search contract.

Specific `pg_search` versions are not pinned in V1 schema. Version
pinning belongs to deployment and infrastructure management, not to
the schema milestone. The Docker image used for M1 verification is
`paradedb/paradedb:pg17` (Postgres 17 baseline). The image bundles
the `pg_search` extension library; the schema migration
`001_extensions.up.sql` activates it with
`CREATE EXTENSION IF NOT EXISTS pg_search`. Production deployments
pin the image by digest; the dev image is overridable through the
compose file.

(Updated 2026-06-19: the previous draft named the tag `stable`,
which does not exist in the upstream catalog. The dev compose now
uses `pg17`. See `docs/AUDITS/FINDINGS.md` F-21.)

## Alternatives Considered

### Alternative 1: PostgreSQL `tsvector` plus GIN

- **Pros**: Standard PostgreSQL feature, no extra extension, broad
  ecosystem support.
- **Cons**: Forces the retrieval pipeline to use `tsvector` GIN
  indexes instead of the BM25 inverted index that `pg_search` was
  approved to provide. This changes the implementation contract
  of the M8 retrieval path, which is drawn from the approved V1
  architecture.
- **Why not**: V1 architecture textually requires `pg_search`. A
  stand-in is architectural drift, not migration pragmatism.

### Alternative 2: Wait for a `pg_search` vendor ADR with full evaluation

- **Pros**: Maximum rigor on extension choice.
- **Cons**: Blocks M1 indefinitely without a clear artifact;
  raises the surface area of M1; defers the choice while every
  downstream milestone's design already assumes `pg_search`.
- **Why not**: Tokenized pinning to version belongs elsewhere;
  a vendor-level ADR can be written later without changing M1
  schema files.

### Alternative 3: Older `pg_search` named extensions

- **Pros**: Possible compatibility with legacy installs.
- **Cons**: Less actively maintained than ParadeDB; mismatched
  feature set against the BM25 retrieval expected by V1.
- **Why not**: Does not match the retrieval capability V1 expects.

## Consequences

### Positive

- Migration files do not need to pin a `pg_search` version.
- The M8 retrieval milestone can assume the BM25 + `pg_search`
  contract without further schema work.
- A single Docker image can host both `pgvector` and `pg_search`.
- Pinning expectations are explicit: architects pin extensions,
  deployment pins versions.

### Negative

- The schema file `migrations/001_extensions.up.sql` is version-
  agnostic, so a future major-version change of `pg_search` is
  not caught at the schema layer. It is caught at deployment.
- ParadeDB is a single-vendor dependency for the lexical path.

### Risks

- A new `pg_search` release changes column conventions, breaking
  migrations. Mitigation: the migration creates the extension
  with `IF NOT EXISTS` and does not assume specific functions.
  CI runs migrations on a fresh image; a release that breaks
  the migration is caught immediately.
- Vendor lock-in. Mitigation: schema narrative still calls it
  `pg_search`; swapping vendors would only change `001_*.up.sql`
  and the deployment image.
