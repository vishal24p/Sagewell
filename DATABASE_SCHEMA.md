# Database Schema

This is the V1 relational schema narrative. V1 tables are:

- users
- documents
- chunks
- audit_logs
- retrieval_logs
- evaluation_results

Additional tables require justification and an ADR.

## Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_search;
```

If the `pg_search` extension name differs in the chosen distribution,
record the installed extension name in a migration note.

## Authorization Fields

Two fields drive every authorization decision in V1:

- `users.department` and `documents.department`
- `users.clearance` and `documents.required_clearance`

The access decision is a pure function:

```text
access = (
    user.department == document.department
    OR
    document.department == "ALL"
)
AND
(
    user.clearance >= document.required_clearance
)
```

Clearance hierarchy:

```text
PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED
```

No other tables, columns, or mechanisms participate in V1 authorization.
There is no `document_acl`, no `permissions`, no `role_permissions`,
no `groups`, and no `group_memberships` in V1.

## users

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `external_subject` | Identity subject (provider-agnostic identifier). |
| `email` | User email. |
| `display_name` | Human-readable name. |
| `status` | Active, disabled, or deleted. |
| `department` | User department. Drives department filter. |
| `clearance` | PUBLIC, INTERNAL, CONFIDENTIAL, or RESTRICTED. Drives clearance filter. |
| `role` | employee, manager, or admin. For UI behavior and auditing only. Does not participate in authorization. |
| `created_at` | Creation timestamp. |
| `updated_at` | Update timestamp. |

## documents

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `source_system` | Connector or source name. |
| `source_id` | Stable source document ID. |
| `title` | Display title. |
| `uri` | Source URI or internal reference. |
| `status` | Active, deleted, or quarantined. |
| `department` | Owning department, or ALL for company-wide documents. |
| `required_clearance` | PUBLIC, INTERNAL, CONFIDENTIAL, or RESTRICTED. |
| `content_checksum` | Hash of normalized content; supports incremental re-ingestion. |
| `created_at` | Creation timestamp. |
| `updated_at` | Update timestamp. |

Unique constraint:

```sql
UNIQUE (source_system, source_id)
```

## chunks

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `document_id` | Document reference. |
| `ordinal` | Chunk order in document. |
| `text` | Chunk text. |
| `text_search` | Lexical search column. |
| `embedding` | Vector embedding. |
| `metadata` | JSON metadata. |
| `token_count` | Approximate token count. |
| `status` | Active or retired. |
| `created_at` | Creation timestamp. |

Indexes:

```sql
CREATE INDEX chunks_document_id_idx ON chunks (document_id);
CREATE INDEX chunks_status_idx ON chunks (status);
CREATE INDEX documents_access_filter_idx
    ON documents (department, required_clearance, status);
CREATE INDEX chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);
```

Lexical index details follow the chosen `pg_search` integration.

## audit_logs

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `actor_user_id` | Actor, if available. |
| `action` | Action name (for example: query.submitted, retrieval.completed, citation.verified, evaluation.completed). |
| `resource_type` | Resource type. |
| `resource_id` | Resource ID. |
| `decision` | Allowed, denied, refused, or failed. |
| `reason_code` | Stable reason code. |
| `correlation_id` | Cross-system trace ID. |
| `metadata` | Redacted JSON metadata. |
| `created_at` | Creation timestamp. |

## retrieval_logs

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `actor_user_id` | Querying user. |
| `query_text` | User query, redacted if needed. |
| `policy_filter` | JSON summary of the access decision. |
| `retrieval_config` | JSON retrieval settings (top-K, RRF K, reranker). |
| `candidate_counts` | JSON counts (dense, bm25, fused, reranked, after access). |
| `correlation_id` | Cross-system trace ID. |
| `created_at` | Creation timestamp. |

## evaluation_results

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `suite` | ragas or rbac_access_outcome. |
| `case_key` | Stable case key. |
| `input` | JSON input. |
| `expected` | JSON expected behavior. |
| `status` | Passed, failed, or skipped. |
| `scores` | JSON metric scores. |
| `failure_reason` | Safe failure reason. |
| `model_config` | JSON capability-based model config. |
| `created_at` | Creation timestamp. |

## Out of V1 Scope

These are NOT V1 tables and must not appear in V1 migrations:

- `document_acl`
- `permissions`
- `role_permissions`
- `groups`
- `group_memberships`
- `user_roles`
- `ingestion_jobs`
- `eval_runs`
- `eval_cases`
- `eval_results` (replaced by `evaluation_results`)

If a future version reintroduces any of these, the change requires an
ADR.

## Schema Rules

- Foreign keys use explicit names.
- Sensitive values are not stored unless required.
- The access decision is computed from `users` and `documents` only.
- Deleted documents do not leave active chunks searchable.
- Migration files include rollback notes where practical.