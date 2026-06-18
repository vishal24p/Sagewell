# Project Status

**Date**: 2026-06-18

## State

Documentation scaffold is being established for Sagewell, a production-oriented Enterprise RAG project. Source implementation files are not present yet.

## Baseline Scope

In scope:

- Single-tenant Enterprise RAG.
- RBAC on retrieval and answer surfaces.
- Prompt-injection guardrails.
- Hybrid retrieval with vector and lexical search.
- Incremental document ingestion.
- FastAPI backend.
- Clean Architecture boundaries.
- LangGraph workflow orchestration.
- LlamaIndex ingestion and retrieval utilities.
- PostgreSQL with `pgvector` and `pg_search`.
- RAGAS plus custom RBAC evals.

Out of scope for the scaffold:

- Code implementation.
- Dependency installation.
- Network calls.
- Deployment provisioning.
- UI design.

## Completed In Scaffold

- Project behavior guide.
- Tooling and CodeGraph guide.
- Skill routing guide.
- Security, RBAC, logging, and evaluation policies.
- Architecture baseline.
- Database schema baseline.
- Runtime workflow baseline.
- Context documents.
- ADR index, template, and initial ADR.
- Local project skill folders.
- Vendored external skill routing under `skills/external/`.
- Project skill routing under `skills/project/`.
- Release and commit skill routing with the local commit/ship gate.

## Current Risks

- Authentication provider is not selected.
- Data retention requirements are not defined.
- First document connectors are not selected.
- Embedding and reranking models are not selected.
- Operational deployment target is not selected.
- No source implementation exists yet, so CodeGraph has no source symbols to index.
- `skills/external/accessibility/SKILL.md` is not present; UI accessibility work must report that missing local route before falling back to outside installed guidance.

## Next Implementation Milestones

1. Define authentication and RBAC integration.
2. Create backend project skeleton and architecture boundaries.
3. Add database migrations for users, roles, documents, chunks, ACLs, ingestion jobs, and audit logs.
4. Implement ingestion pipeline with idempotent document versioning.
5. Implement retrieval with RBAC filters applied before ranking output.
6. Implement LangGraph answer workflow with prompt-injection guardrails.
7. Add RAGAS and custom RBAC regression evals.
