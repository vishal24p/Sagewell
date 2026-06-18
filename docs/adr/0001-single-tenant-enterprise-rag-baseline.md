# ADR-0001: Single-Tenant Enterprise RAG Baseline

**Date**: 2026-06-18
**Status**: accepted
**Deciders**: Project owner and implementation agents

## Context

The project needs a production-oriented baseline for enterprise retrieval over private documents. The system must support internal access differences even though it is single tenant. Retrieval quality, authorization, prompt-injection resistance, and evaluation need to be designed together instead of added after the fact.

## Decision

Use a single-tenant Enterprise RAG architecture with RBAC, department and clearance filters, prompt-injection guardrails, hybrid retrieval, incremental ingestion, FastAPI, Clean Architecture, LangGraph workflow orchestration, LlamaIndex ingestion and retrieval utilities, PostgreSQL, `pgvector`, `pg_search`, RAGAS, and custom RBAC evals.

## Alternatives Considered

### Alternative 1: Simple Chat Over Documents

- **Pros**: Faster to prototype and easier to explain.
- **Cons**: Weak access-control guarantees, limited traceability, and poor regression coverage.
- **Why not**: The project target is enterprise use, where citation leaks and ACL bypasses are unacceptable.

### Alternative 2: Vector-Only Retrieval

- **Pros**: Simple retrieval pipeline and common RAG pattern.
- **Cons**: Poor exact-match behavior for names, codes, policy IDs, and legal terms.
- **Why not**: Enterprise search needs both semantic matching and lexical precision.

### Alternative 3: Monolithic Framework-Centric Design

- **Pros**: Faster initial scaffolding.
- **Cons**: Business rules become coupled to framework and vendor details.
- **Why not**: Clean Architecture keeps authorization, retrieval policy, and workflow behavior testable.

## Consequences

### Positive

- RBAC, department, and clearance controls are part of retrieval design from the start.
- Prompt-injection guardrails are part of the answer workflow.
- Hybrid retrieval can handle semantic and exact-match queries.
- Incremental ingestion supports production document updates.
- Evaluation can detect retrieval and access-control regressions.

### Negative

- More components must be wired before a demo feels complete.
- Database migrations and indexes need careful design.
- Evaluation datasets must be maintained as product behavior changes.

### Risks

- RBAC, department, or clearance filters can be accidentally bypassed if adapters expose raw retrieval paths. Mitigation: keep retrieval behind application use cases and add deny-path evals.
- Prompt-injection detection can create false positives. Mitigation: record reason codes and tune with a labeled dataset.
- Hybrid retrieval can produce ranking instability. Mitigation: version retrieval configuration and track eval deltas.
