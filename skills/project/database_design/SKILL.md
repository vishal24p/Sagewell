# Database Design Skill

Use this local skill for schema, migration, index, and query design work.

## Inputs

- `DATABASE_SCHEMA.md`
- `POLICIES.md`
- Relevant ingestion and retrieval workflows.

## Checklist

- Every document and chunk can be traced to source, version, checksum, and ingestion job.
- ACL lookup paths are indexed before retrieval ships.
- Deleted or retired documents cannot leave active chunks searchable.
- Vector and lexical indexes are compatible with policy filters.
- Audit events include actor, action, resource, decision, reason code, and correlation ID.
- Evaluation results record dataset, model, and retrieval configuration versions.

## Done Condition

The database change preserves traceability, access control, rollback clarity, and query performance assumptions.
