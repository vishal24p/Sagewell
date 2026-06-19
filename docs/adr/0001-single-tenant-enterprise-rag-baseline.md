# ADR-0001: Single-Tenant Enterprise RAG V1 Baseline

**Date**: 2026-06-19
**Status**: accepted
**Deciders**: Project owner and implementation agents

## Context

Sagewell needs a production-oriented baseline for enterprise retrieval
over private documents. Authorization must be explicit, retrieval must
combine dense and lexical signals, prompt protection must be on the
primary request path, and evaluation must cover both quality and
access outcomes. Scope must be tight enough to ship V1 without
introducing mechanisms that belong to a later version.

## Decision

Sagewell V1 is a single-company, single-tenant enterprise RAG
baseline. The V1 scope is:

- Authorization: department + clearance only.
- Retrieval: dense + BM25 + RRF fusion + cross-encoder reranking.
- Workflow orchestration: LangGraph.
- Document loading, semantic chunking, ingestion, and retrieval
  abstractions: LlamaIndex.
- Data store: PostgreSQL with `pgvector` and `pg_search`.
- Authentication: JWT.
- Prompt protection: regex guard and LLM guard on the primary
  request path.
- Citation verification by re-running the access decision on every
  cited document.
- Incremental re-ingestion.
- Evaluation: RAGAS and the RBAC Access Outcome Suite (both
  required).
- Models: capability-based. Generation Model, Embedding Model,
  Reranker Model, Guardrail Model. No specific model is pinned.
- V1 tables: users, documents, chunks, audit_logs, retrieval_logs,
  evaluation_results.

The access decision is a single pure function:

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

The access decision runs at three boundaries for every request:
pre-retrieval (filter), post-rerank (drop), and citation verification
(re-check).

## Alternatives Considered

### Alternative 1: ACL engine with document_acl and permissions

- **Pros**: Familiar enterprise pattern. Supports fine-grained grants.
- **Cons**: Out of V1 scope. Adds tables and resolution logic that
  are not required for V1.
- **Why not**: V1 is explicitly department + clearance only. ACL
  belongs to a later version and requires its own ADR.

### Alternative 2: Group-based authorization

- **Pros**: Common RBAC pattern.
- **Cons**: Out of V1 scope. Adds `groups` and `group_memberships`
  tables that are not required.
- **Why not**: Department + clearance is sufficient for V1.

### Alternative 3: Vector-only retrieval

- **Pros**: Simpler pipeline.
- **Cons**: Weak on exact match, codes, policy IDs, legal terms.
- **Why not**: V1 mandates hybrid retrieval (dense + BM25 + RRF +
  cross-encoder).

### Alternative 4: Rerank omission

- **Pros**: Lower latency, fewer components.
- **Cons**: Lower quality, weaker signal on tie cases.
- **Why not**: V1 mandates cross-encoder reranking.

### Alternative 5: Defer prompt protection to a later phase

- **Pros**: Faster initial build.
- **Cons**: The primary request path is the risk surface; deferring
  prompt protection creates an exploitable window.
- **Why not**: V1 runs the regex guard and LLM guard on every
  request.

### Alternative 6: External IAM (OIDC, Okta, Entra, LDAP)

- **Pros**: Off-the-shelf identity.
- **Cons**: Out of V1 scope.
- **Why not**: V1 is JWT-based. A future version can introduce an
  external IAM via its own ADR.

## Consequences

### Positive

- Tight scope. The V1 boundary is clear: one access decision, one
  retrieval pipeline, one workflow shape.
- The access decision is testable as a pure function.
- The retrieval pipeline is reproducible end-to-end.
- Prompt protection runs on the primary request path.
- Evaluation covers both quality and access outcomes.

### Negative

- Department + clearance may be insufficient for some organizations.
- No ACL engine means fine-grained grants are unavailable until a
  later version.
- No external IAM means identity federation must be added later.

### Risks

- If the access decision is bypassed at any boundary, the system
  leaks. Mitigation: invoke the access decision at three boundaries
  and add deny-path cases to the RBAC Access Outcome Suite.
- If the retrieval pipeline drops reranking, quality drops.
  Mitigation: the release gate requires the full pipeline.
- If prompt protection is moved out of the primary request path, the
  attack surface opens. Mitigation: the workflow definition locks
  prompt protection between retrieval and generation.

## Out of V1 Scope

The following are not V1 and require their own ADR:

- ACL engine, `document_acl`, `permissions`, `role_permissions`.
- Groups, `group_memberships`, group-based authorization.
- OIDC, Okta, Entra ID, LDAP, identity federation, external IAM.
- Permission resolution engines.
- Multi-tenant isolation.
- Pinning specific model identifiers or versions.