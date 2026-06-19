# ADR-0004: Embedding Column Uses Fixed Dimension `vector(1536)`

**Date**: 2026-06-19
**Status**: accepted
**Deciders**: Project maintainers
**Closes**: M1 Engineering Finding F-3.

## Context

`chunks.embedding` carries the dense retrieval vector. The V1
architecture mandates hybrid retrieval (Dense + BM25 + RRF +
cross-encoder) and uses Postgres `pgvector` for the dense path.
`pgvector` requires a per-column dimension; mismatched dimensions
produce `different vector dimensions` errors at query time.

V1 is capability-based for models: the `Embedding Model` capability
is not pinned to a specific identifier or version. Determining
the dimension requires choosing a capability range, not a vendor.

## Decision

The `chunks.embedding` column is declared as `vector(1536)`.
This dimension is consistent with the candidate range named in
`MEMORY.md` (`D-002`): "1024-1536 dimensions". 1536 is the upper
bound, which is the most common in production-grade embedding
models. Lowering the dimension later is cheaper than raising it
because lower dimensions can fit inside a higher-dimensional
column after a flag-day reindex; upper bound is the conservative
choice.

If a future ADR changes the capability and the lower bound (1024)
becomes the right choice, the column can be migrated:
`ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(1024)`
using a fresh embedding computation. That ALTER is itself an
ADR-driven change because it changes a schema invariant.

## Alternatives Considered

### Alternative 1: `vector` with no dimension

- **Pros**: Flexibility at the schema level.
- **Cons**: `pgvector` defaults inconsistently across versions;
  the HNSW index assumes a single dimension; rows with different
  dimensions crash at retrieval time rather than at insert time.
- **Why not**: M1 already encodes the principle of fail-closed,
  fail-fast. Type-level enforcement belongs in the schema.

### Alternative 2: `vector(1024)`

- **Pros**: Half the storage cost of `vector(1536)`.
- **Cons**: Forces a later migration if the capability picks a
  larger model. The migration itself is non-trivial because rows
  must be recomputed.
- **Why not**: Upper bound is the conservative choice for V1.

### Alternative 3: Pin a specific model and pin the dimension off it.

- **Pros**: Eliminates ambiguity.
- **Cons**: Breaks the capability-based model policy. Disallowed
  for V1 docs and code.
- **Why not**: Architecture decision.

## Consequences

### Positive

- `chunks.embedding` stores exactly one dimension. The HNSW
  index in `003_indexes.up.sql` is justified.
- Arithmetic against the embedding column is straightforward;
  no runtime dimension checks.

### Negative

- 1536 floats per chunk is 6 KB of storage per row. Acceptable
  for V1; quantified here so future milestones are not surprised.
- A future Embedding Model capability change is non-free.

### Risks

- A capability ADR could change the dimension. Mitigation: this
  ADR names the change path and the rule that any dimension
  change is itself ADR-driven.
