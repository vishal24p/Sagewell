# Database Design Skill

Use this skill for V1 schema, migration, index, and query design.

## Inputs

- `DATABASE_SCHEMA.md`
- `POLICIES.md`
- Relevant ingestion and retrieval workflows.

## V1 Tables (Authoritative)

- users
- documents
- chunks
- audit_logs
- retrieval_logs
- evaluation_results

Any new table requires justification and an ADR.

## Checklist

- `users` carries `department`, `clearance`, and `role`. Role is for
  UI behavior and auditing only; it does not participate in
  authorization.
- `documents` carries `department`, `required_clearance`, and
  `content_checksum` for incremental re-ingestion.
- `chunks` carries text, `text_search`, `embedding`, status, and
  metadata. Vector index uses `pgvector` (HNSW). Lexical index uses
  `pg_search`.
- `audit_logs` records actor, action, resource, decision,
  `reason_code`, `correlation_id`, and redacted metadata.
- `retrieval_logs` records `actor_user_id`, `query_text`,
  `policy_filter` JSON, `retrieval_config` JSON, `candidate_counts`
  JSON, and `correlation_id`.
- `evaluation_results` records `suite` (`ragas` or
  `rbac_access_outcome`), `case_key`, `input`, `expected`, `status`,
  `scores`, `failure_reason`, and `model_config`.
- Deleted documents do not leave active chunks searchable.
- Migrations include rollback notes where practical.

## Out of V1

These do not appear in V1 migrations and must not be reintroduced
without an ADR:

- `document_acl`
- `permissions`, `role_permissions`, `user_roles`
- `groups`, `group_memberships`
- `ingestion_jobs`, `eval_runs`, `eval_cases`, `eval_results`

## Done Condition

The database change preserves traceability, the access decision
remains derivable from `users` and `documents` only, and query
performance assumptions are documented.