# Database Schema

This is the baseline relational schema for the Enterprise RAG system. Exact column types may be refined during implementation, but the access-control and traceability relationships should remain intact.

## Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_search;
```

If the exact `pg_search` extension name differs in the chosen distribution, document the installed extension in a migration note.

## Entity Overview

```text
users
roles
permissions
user_roles
groups
group_memberships
collections
documents
document_versions
chunks
document_acl
chunk_acl_snapshot
ingestion_jobs
retrieval_runs
answers
citations
audit_events
eval_runs
eval_cases
eval_results
```

## Identity And RBAC

### users

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `external_subject` | Identity-provider subject. |
| `email` | User email. |
| `display_name` | Human-readable name. |
| `status` | Active, disabled, or deleted. |
| `department` | Primary department for department-scoped retrieval. |
| `clearance_level` | PUBLIC, INTERNAL, CONFIDENTIAL, or RESTRICTED. |
| `created_at` | Creation timestamp. |
| `updated_at` | Update timestamp. |

### roles

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `name` | Unique role name. |
| `description` | Role description. |
| `created_at` | Creation timestamp. |

### permissions

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `action` | Action name, such as `document.read`. |
| `description` | Permission description. |

### role_permissions

| Column | Purpose |
|---|---|
| `role_id` | Role reference. |
| `permission_id` | Permission reference. |

### user_roles

| Column | Purpose |
|---|---|
| `user_id` | User reference. |
| `role_id` | Role reference. |
| `scope_type` | Global, collection, or document. |
| `scope_id` | Optional scoped resource ID. |

### groups

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `name` | Group name. |
| `external_ref` | Optional identity-provider group reference. |

### group_memberships

| Column | Purpose |
|---|---|
| `group_id` | Group reference. |
| `user_id` | User reference. |

## Documents And Chunks

### collections

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `name` | Collection name. |
| `description` | Collection description. |
| `default_acl_mode` | Restricted or inherited. |
| `created_at` | Creation timestamp. |

### documents

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `collection_id` | Collection reference. |
| `source_system` | Connector or source name. |
| `source_id` | Stable source document ID. |
| `title` | Display title. |
| `uri` | Source URI or internal reference. |
| `status` | Active, deleted, quarantined, or failed. |
| `department` | Owning department, or ALL for company-wide documents. |
| `clearance_level` | PUBLIC, INTERNAL, CONFIDENTIAL, or RESTRICTED. |
| `created_at` | Creation timestamp. |
| `updated_at` | Update timestamp. |

Unique constraint:

```sql
UNIQUE (source_system, source_id)
```

### document_versions

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `document_id` | Document reference. |
| `source_version` | Version from source system, if available. |
| `content_checksum` | Hash of normalized content. |
| `metadata` | JSON metadata. |
| `ingestion_job_id` | Job that produced this version. |
| `created_at` | Creation timestamp. |

### chunks

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `document_id` | Document reference. |
| `document_version_id` | Document version reference. |
| `ordinal` | Chunk order in document. |
| `text` | Chunk text. |
| `text_search` | Search document or generated search column. |
| `embedding` | Vector embedding. |
| `metadata` | JSON metadata. |
| `token_count` | Approximate token count. |
| `status` | Active or retired. |
| `created_at` | Creation timestamp. |

Indexes:

```sql
CREATE INDEX chunks_document_version_idx ON chunks (document_version_id);
CREATE INDEX chunks_status_idx ON chunks (status);
CREATE INDEX documents_access_filter_idx ON documents (department, clearance_level, status);
CREATE INDEX chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
```

Lexical index details should follow the chosen `pg_search` integration.

## Access Control

Classification is a hard filter. `department` and `clearance_level` on `documents` are evaluated before ACL grants are considered.

### document_acl

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `document_id` | Document reference. |
| `principal_type` | User, group, or role. |
| `principal_id` | Principal ID. |
| `permission` | Read, write, administer. |
| `effect` | Allow or deny. |
| `created_at` | Creation timestamp. |

Required index:

```sql
CREATE INDEX document_acl_lookup_idx
ON document_acl (document_id, principal_type, principal_id, permission, effect);
```

### chunk_acl_snapshot

| Column | Purpose |
|---|---|
| `chunk_id` | Chunk reference. |
| `acl_hash` | Hash of ACL state at indexing time. |
| `allowed_user_ids` | Optional denormalized user IDs for small deployments. |
| `allowed_group_ids` | Optional denormalized group IDs. |
| `allowed_role_ids` | Optional denormalized role IDs. |

Use this table only as an optimization. `document_acl` remains the authority unless implementation explicitly changes that decision in an ADR.

## Ingestion

### ingestion_jobs

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `source_system` | Connector name. |
| `status` | Pending, running, succeeded, failed, canceled. |
| `started_by` | User or service account. |
| `started_at` | Start timestamp. |
| `finished_at` | Finish timestamp. |
| `stats` | JSON counts and timings. |
| `error_code` | Stable failure code. |
| `error_message` | Safe failure message. |

## Retrieval And Answers

### retrieval_runs

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `actor_user_id` | Querying user. |
| `query_text` | User query, redacted if needed. |
| `policy_filter_summary` | JSON summary of applied filters. |
| `retrieval_config` | JSON retrieval settings. |
| `created_at` | Creation timestamp. |

### answers

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `retrieval_run_id` | Retrieval run reference. |
| `answer_text` | Generated answer, redacted if needed. |
| `model` | Generation model identifier. |
| `finish_reason` | Completion status. |
| `created_at` | Creation timestamp. |

### citations

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `answer_id` | Answer reference. |
| `chunk_id` | Cited chunk reference. |
| `document_id` | Cited document reference. |
| `quote` | Short cited quote or excerpt. |
| `rank` | Citation rank. |

## Audit And Evaluation

### audit_events

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `actor_user_id` | Actor, if available. |
| `action` | Action name. |
| `resource_type` | Resource type. |
| `resource_id` | Resource ID. |
| `decision` | Allowed, denied, failed. |
| `reason_code` | Stable reason code. |
| `correlation_id` | Cross-system trace ID. |
| `metadata` | Redacted JSON metadata. |
| `created_at` | Creation timestamp. |

### eval_runs

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `suite_name` | Evaluation suite. |
| `dataset_version` | Dataset version. |
| `retrieval_config` | JSON retrieval config. |
| `model_config` | JSON model config. |
| `status` | Running, succeeded, failed. |
| `created_at` | Creation timestamp. |

### eval_cases

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `suite_name` | Suite name. |
| `case_key` | Stable case key. |
| `input` | JSON input. |
| `expected` | JSON expected behavior. |
| `tags` | JSON tags. |

### eval_results

| Column | Purpose |
|---|---|
| `id` | Primary key. |
| `eval_run_id` | Eval run reference. |
| `eval_case_id` | Eval case reference. |
| `status` | Passed, failed, skipped. |
| `scores` | JSON metric scores. |
| `failure_reason` | Safe failure reason. |

## Schema Rules

- Foreign keys should use explicit names.
- Sensitive values must not be stored unless required.
- ACL lookups must be indexed before retrieval code ships.
- Deleted documents must not leave active chunks searchable.
- Migration files must include rollback notes where practical.
