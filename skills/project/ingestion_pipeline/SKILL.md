# Ingestion Pipeline Skill

Use this skill for V1 incremental re-ingestion.

## Inputs

- `WORKFLOWS.md`
- `DATABASE_SCHEMA.md`
- `POLICIES.md`

## Scope

V1 ingestion is incremental re-ingestion through LlamaIndex. There is
no `ingestion_jobs` table in V1; the job outcome is recorded in
`audit_logs`.

## Checklist

- Ingestion is idempotent by `documents.content_checksum`.
- Unchanged documents are skipped.
- Changed documents are re-loaded through LlamaIndex.
- LlamaIndex semantic chunking produces new chunks.
- New chunks are embedded using the Embedding Model.
- New chunks are written; replaced chunks are retired atomically.
- A failed document does not fail the whole job unless the connector
  requires all-or-nothing behavior.
- A failed embedding write must not leave partially active chunks.
- Deleted source documents retire searchable chunks.
- Job outcome is recorded in `audit_logs` with `correlation_id`.

## LlamaIndex Responsibilities

LlamaIndex handles document loading, semantic chunking, ingestion,
and retrieval abstractions. It does not handle authorization,
workflow orchestration, or business rules.

## Done Condition

The ingestion change can be retried safely and leaves no partially
active searchable state after failure.