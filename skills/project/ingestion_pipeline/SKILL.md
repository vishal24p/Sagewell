# Ingestion Pipeline Skill

Use this local skill for document connectors, parsing, chunking, embedding, and reindexing.

## Inputs

- `WORKFLOWS.md`
- `DATABASE_SCHEMA.md`
- `POLICIES.md`

## Checklist

- Ingestion is idempotent by source ID, source version, and checksum.
- Unchanged documents are skipped.
- Changed documents produce a new document version.
- Replaced chunks are retired atomically.
- Embeddings and chunk rows cannot become inconsistent.
- ACL snapshots are updated when source permissions change.
- Job stats and failures are recorded with safe error messages.

## Done Condition

The ingestion change can be retried safely and leaves no partially active searchable state after failure.
