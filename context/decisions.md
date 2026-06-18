# Decisions

This file summarizes decisions for quick context. Detailed architectural records live in `docs/adr/`.

## Accepted

- Use a single-tenant Enterprise RAG baseline.
- Use RBAC as a hard retrieval constraint.
- Use department and clearance as hard classification filters.
- Treat retrieved document content as untrusted.
- Use FastAPI and Clean Architecture for backend boundaries.
- Use LangGraph for workflow orchestration.
- Use LlamaIndex for ingestion and retrieval utilities.
- Use PostgreSQL with `pgvector` and `pg_search`.
- Use RAGAS plus custom RBAC evals.
- Keep `AGENTS.md` short and route detail to dedicated docs.

## Pending

- Authentication provider.
- Connector scope.
- Embedding model.
- Reranker model.
- Deployment target.
- Data retention requirements.
- Audit log retention period.
