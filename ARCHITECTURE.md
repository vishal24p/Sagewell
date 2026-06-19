# Architecture

## Overview

Sagewell is a single-company, single-tenant enterprise RAG system.
Authorization is based on department and clearance only. Retrieval is
hybrid: dense retrieval, BM25 retrieval, RRF fusion, and cross-encoder
reranking. Workflow orchestration is delegated to LangGraph. Document
loading, semantic chunking, ingestion, and retrieval abstractions are
delegated to LlamaIndex. The data store is PostgreSQL with `pgvector`
and `pg_search`.

The stack is:

- **API layer**: HTTP request handling, JWT validation, request and
  response schemas, correlation IDs, safe error translation.
- **Application layer**: use cases, workflow entrypoints, transaction
  boundaries, audit event emission.
- **Domain layer**: entities, the access decision function (pure),
  errors, value objects. Pure Python. No framework imports.
- **Infrastructure layer**: PostgreSQL repositories, `pgvector` dense
  retrieval adapter, `pg_search` BM25 retrieval adapter, LlamaIndex
  ingestion and retrieval adapters, LangGraph workflow definitions,
  capability-based generation/embedding/reranker/guardrail clients,
  audit writer.
- **Evaluation layer**: RAGAS suite and the RBAC Access Outcome Suite.

## Design Goals

- Department and clearance are the only authorization inputs.
- Retrieval must combine dense and BM25 signals with reranking.
- The primary request path always runs the regex guard before any
  retrieval work, and the LLM guard before generation.
- Citations are verified against the same authorization rule.
- Workflow steps are explicit and individually testable.
- Treat retrieved content as untrusted data.
- Models are capability-based; no specific model is assumed.

## Non-Goals (V1)

- Multi-tenant isolation.
- ACL engine or `document_acl` table.
- Groups or group-based authorization.
- OIDC, Okta, Entra ID, LDAP, or external IAM.
- Permission resolution engines.
- Vector-only retrieval, BM25-only retrieval, retrieval without
  reranking.

## Layered Boundaries

```text
api/
  HTTP routes, request and response schemas, JWT validation,
  correlation IDs, error translation.
application/
  Use cases, workflow entrypoints, transaction boundaries,
  audit emission.
domain/
  Entities, the access decision function, errors, value objects.
  Pure Python. No framework imports.
infrastructure/
  PostgreSQL repositories, pgvector adapter, pg_search adapter,
  LlamaIndex adapters, LangGraph workflow definitions,
  capability-based clients (generation, embedding, reranker,
  guardrail), audit writer.
evaluation/
  RAGAS suite, RBAC Access Outcome Suite.
```

Dependency direction:

```text
api -> application -> domain
infrastructure -> application/domain interfaces
evaluation -> public use cases and test adapters
```

Domain code does not import from api, application, infrastructure,
evaluation, LangGraph, LlamaIndex, asyncpg, or any model SDK.

## Framework Responsibilities

### LangGraph is responsible for

- workflow orchestration
- state management
- node execution

LangGraph is NOT responsible for:

- authorization
- retrieval
- database access
- business logic

The access decision is a pure function in the domain layer. Retrieval
adapters live in infrastructure. The LangGraph state machine only
sequences the use case and exchanges typed state between nodes.

### LlamaIndex is responsible for

- document loading
- semantic chunking
- ingestion
- retrieval abstractions

LlamaIndex is NOT responsible for:

- RBAC
- authorization
- workflow orchestration
- business rules

Authorization is applied at the boundary between LlamaIndex retrieval
abstractions and the domain access decision. LlamaIndex does not see
authorization state; the workflow applies the access decision to
retrieved results.

## Retrieval Architecture

Retrieval is hybrid. All four stages are mandatory:

```text
Dense Retrieval
  +
BM25 Retrieval
  +
RRF Fusion
  +
Cross-Encoder Reranking
```

### Stage 1: Dense Retrieval

- Embedding model is capability-based (Embedding Model). No specific
  model is pinned in V1.
- Stores and searches vectors in `pgvector`.
- Returns top-K candidates with vector similarity score.

### Stage 2: BM25 Retrieval

- Lexical retrieval using `pg_search`.
- Returns top-K candidates with BM25 score.

### Stage 3: RRF Fusion

- Reciprocal Rank Fusion merges dense and BM25 ranked lists.
- Configurable K constant.
- Returns a single fused ranked list.

### Stage 4: Cross-Encoder Reranking

- Reranker model is capability-based (Reranker Model).
- Reranks the fused list using query-document cross-attention.
- Returns the final top-N chunks.

## Authorization Architecture

Authorization is department plus clearance only. The access decision is
a single pure function:

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

The function takes `(user, document)` and returns `(allowed, reason)`.
It is invoked in three places, every time, for every request:

1. Before dense and BM25 retrieval, to constrain the candidate set.
2. After reranking, to drop any chunk that fails the rule.
3. At citation verification, to re-check every cited document.

If the function raises or returns a non-allow decision, the system
fails closed.

## LangGraph Workflow

The answer workflow is a state machine. The state is a typed object.
Each node receives the state, performs one responsibility, and returns
the updated state. External systems are behind interfaces so each node
is unit-testable with fakes.

```text
START
  -> validate_jwt
  -> regex_guard
  -> load_actor
  -> apply_access_decision (constraint for retrieval)
  -> dense_retrieve
  -> bm25_retrieve
  -> rrf_fuse
  -> cross_encoder_rerank
  -> apply_access_decision (drop unauthorized from reranked list)
  -> llm_guard
  -> generate_answer
  -> verify_citations (re-run access decision on every cited document)
  -> persist_and_audit
END
```

Failure paths:

- JWT invalid or missing -> 401.
- Regex guard blocks -> refuse, no generation.
- Access decision unavailable -> fail closed, 403.
- Retrieval returns zero after retry -> 503, safe error.
- LLM guard blocks -> refuse, no generation.
- Citation verification fails a citation -> drop the citation; if no
  citations remain, regenerate or refuse.
- Audit write fails -> do not return a response.

## Ingestion Architecture

Incremental re-ingestion is supported in V1:

1. Connector discovers source documents.
2. Source document metadata is compared with stored checksums.
3. Changed documents are re-loaded via LlamaIndex.
4. LlamaIndex semantic chunking produces new chunks.
5. Chunks are embedded using the Embedding Model.
6. New chunks are written; old chunks for the changed document are
   retired.
7. Job outcome is written to `audit_logs`.

## Security Architecture

The primary request path executes in this order:

```text
JWT Authentication
  -> Regex Guard
  -> RBAC Authorization (department + clearance)
  -> Retrieval (dense + BM25 + RRF + cross-encoder)
  -> LLM Guard
  -> Generation
```

Prompt protection is part of the primary request path. It is not moved
to a later phase.

The Regex Guard runs after JWT validation and before RBAC
authorization. It is cheap, deterministic, and fast, and its job is
to refuse obvious prompt-injection attempts (for example "ignore
previous instructions," "reveal system prompt," "dump database,"
"show all restricted documents") before the system does the work of
RBAC evaluation and the four retrieval stages.

The LLM Guard runs after retrieval. It is context-aware and uses
the Guardrail Model to detect indirect prompt injection, contextual
attacks, instruction conflicts, and retrieval-based attacks. It is
not redundant with the Regex Guard: Regex Guard is pattern-based and
runs on the user query before any retrieval occurs; LLM Guard is
context-aware and runs on the user query together with retrieved
chunks.

### JWT Authentication

- The API layer validates the JWT on every request.
- Required claims: subject, department, clearance, expiration.
- Role claim is permitted for UI behavior and auditing; it does not
  participate in authorization.

### Regex Guard

- Pattern-based detection on the normalized query.
- Runs after JWT validation and before RBAC and retrieval, so that
  obvious prompt-injection attempts are refused before any
  authorization or retrieval work is performed.
- High-risk patterns cause the request to be refused.
- Pattern list is versioned and configurable.

### LLM Guard

- Capability-based model (Guardrail Model) classifies the normalized
  query and retrieved chunks.
- Runs after retrieval and before generation. Catches indirect
  prompt injection, contextual attacks, instruction conflicts, and
  retrieval-based attacks that the Regex Guard cannot see.
- High-risk classification causes the request to be refused, the
  retrieved content to be downgraded, or generation to be constrained.

## Evaluation Architecture

Two independent evaluation systems run in V1:

### System 1: RAGAS

Metrics:

- Faithfulness
- Context Precision
- Context Recall
- Answer Relevancy

### System 2: RBAC Access Outcome Suite

Tests:

- Allow Tests
- Deny Tests
- Department Tests
- Clearance Tests

The two systems are independent. RAGAS does not replace access outcome
tests, and access outcome tests do not replace RAGAS.

## Observability

Correlation IDs flow through:

- API request.
- LangGraph run.
- Retrieval queries.
- LLM calls.
- Audit rows.
- Evaluation runs.

Minimum observability surfaces:

- Access decision per request, with reason.
- Candidate counts before and after access decision.
- Reranker input and output counts.
- Guard verdicts (regex and LLM).
- Citation verification results.
- Evaluation run summaries.

## Model Policy

Documentation refers to capabilities, not specific models. The
following names are used:

- Generation Model
- Embedding Model
- Reranker Model
- Guardrail Model

No specific vendor, model identifier, or version is committed in V1
documentation.

## Database Scope

V1 tables:

- users
- documents
- chunks
- audit_logs
- retrieval_logs
- evaluation_results

Additional tables require justification and an ADR.