# Architecture

## Overview

Sagewell is a single-tenant retrieval-augmented generation system for controlled enterprise knowledge access. It combines RBAC, department and clearance filters, prompt-injection guardrails, hybrid retrieval, incremental ingestion, and evaluation gates.

The baseline stack is:

- FastAPI for HTTP APIs.
- Clean Architecture for boundaries.
- LangGraph for workflow orchestration.
- LlamaIndex for ingestion and retrieval utilities.
- PostgreSQL for relational data.
- `pgvector` for embeddings.
- `pg_search` for lexical and hybrid retrieval support.
- RAGAS and custom RBAC evals for regression checks.

## Design Goals

- Enforce access control throughout retrieval and generation.
- Make ingestion incremental, idempotent, and observable.
- Keep workflow steps explicit and testable.
- Support hybrid retrieval with metadata filters and citations.
- Treat retrieved content as untrusted input.
- Keep infrastructure adapters replaceable.

## Non-Goals

- Multi-tenant SaaS isolation.
- Public anonymous search.
- Fine-tuning as a first dependency.
- UI as part of the initial baseline.

## Clean Architecture Boundaries

```text
api/
  FastAPI routes, request validation, response models
application/
  use cases, workflow entrypoints, authorization orchestration
domain/
  entities, policies, value objects, errors
infrastructure/
  database repositories, vector search, LLM clients, connectors
evals/
  RAGAS suites, RBAC regression suites, prompt-injection tests
```

Dependency direction:

```text
api -> application -> domain
infrastructure -> application/domain interfaces
evals -> public use cases and test adapters
```

Domain code must not depend on FastAPI, LangGraph, LlamaIndex, or database clients.

## Core Components

### API Layer

Responsibilities:

- Authenticate requests.
- Validate request and response shapes.
- Attach correlation IDs.
- Translate domain errors into safe HTTP responses.
- Avoid embedding authorization logic directly in route handlers.

Expected API areas:

- Query and answer.
- Document ingestion.
- Collection and document management.
- RBAC administration.
- Evaluation runs.
- Health and readiness.

### Application Layer

Responsibilities:

- Coordinate use cases.
- Call domain policies.
- Start LangGraph workflows.
- Apply transaction boundaries.
- Record audit events.
- Keep orchestration independent from transport details.

Expected use cases:

- Submit query.
- Start ingestion job.
- Reindex document.
- Update document ACL.
- Run evaluation suite.
- Inspect retrieval trace.

### Domain Layer

Responsibilities:

- Model users, roles, permissions, documents, chunks, citations, and policy decisions.
- Define RBAC, department, clearance, and prompt-risk policy rules.
- Define errors that can be safely surfaced.
- Preserve invariants independent of storage or framework.

### Infrastructure Layer

Responsibilities:

- PostgreSQL repositories.
- `pgvector` queries.
- `pg_search` lexical queries.
- LlamaIndex document parsing, chunking, and retrieval adapters.
- LangGraph node implementations.
- LLM and embedding clients.
- Connector clients.
- Audit log writer.

## Retrieval Architecture

Retrieval is hybrid:

1. Normalize the user query.
2. Resolve actor permissions.
3. Apply RBAC filters before candidate retrieval.
4. Run vector search over authorized chunks.
5. Run lexical search over authorized chunks.
6. Merge and rerank candidates.
7. Apply citation and document access checks again.
8. Pass bounded context to generation.

RBAC, department, and clearance filters are not optional ranking hints. They are hard constraints.

Required classification filters:

```text
user.clearance >= document.clearance
AND
(user.department = document.department OR document.department = "ALL")
```

ACLs can restrict access further through user, group, role, collection, and document grants.

## LangGraph Workflow

The answer workflow should use explicit nodes:

```text
validate_request
  -> authorize_query
  -> classify_intent
  -> retrieve_candidates
  -> detect_prompt_injection
  -> rerank_and_pack_context
  -> generate_answer
  -> verify_citations
  -> audit_and_return
```

Each node should accept and return typed state. Nodes that call external systems must be isolated behind interfaces so they can be tested with fakes.

## Ingestion Architecture

Ingestion is incremental and idempotent:

1. Connector discovers source documents.
2. Source document metadata is compared with stored versions.
3. Changed documents are parsed.
4. Text is chunked.
5. Chunks are embedded.
6. Chunks and embeddings are written in one consistent update.
7. Old chunks are retired or replaced.
8. Search indexes are refreshed.
9. Job status and audit events are recorded.

Every document version should be traceable to source ID, source version, checksum, ingestion job, and ACL snapshot.

## Security Model

Security is enforced in layers:

- API authentication.
- Use-case authorization.
- Query-time retrieval filters.
- Department and clearance filters.
- Citation access checks.
- Prompt-injection checks.
- Audit logging.

If any policy check fails or cannot complete, the system fails closed.

## Evaluation Architecture

Evaluation suites include:

- RAGAS answer faithfulness.
- RAGAS context precision and recall.
- Citation validity.
- RBAC allow and deny tests.
- Prompt-injection resistance tests.
- Retrieval regression tests for known queries.

Evaluation results must be stored with dataset version, code version, model version, and retrieval configuration.

## Observability

Use correlation IDs across:

- API request.
- Application use case.
- LangGraph run.
- Retrieval queries.
- LLM calls.
- Audit events.
- Evaluation runs.

Minimum traces:

- Query input classification.
- Authorized filter summary.
- Candidate counts before and after filters.
- Selected citations.
- Policy decisions.
- Error reason codes.
