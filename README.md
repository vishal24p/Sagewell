# Sagewell

Repository name: `sagewell`

Sagewell is a production-oriented single-tenant Enterprise RAG system for controlled access to private organizational knowledge. The project focuses on authorization-aware retrieval, citations, prompt-injection resistance, incremental ingestion, and regression evaluation.

## Architecture Summary

- FastAPI exposes API boundaries for query, ingestion, document management, RBAC administration, evaluation, and health checks.
- Application use cases coordinate authorization, transactions, audit events, and LangGraph workflows.
- Domain code owns users, roles, permissions, documents, chunks, citations, ACLs, and policy decisions.
- Infrastructure adapters provide PostgreSQL repositories, `pgvector` search, `pg_search` lexical retrieval, LlamaIndex ingestion and retrieval utilities, LLM clients, connector clients, and audit writing.
- Evaluation covers RAGAS quality checks, citation validity, RBAC allow and deny cases, prompt-injection resistance, and retrieval regression.

## Documentation

- `ARCHITECTURE.md` explains system boundaries and runtime components.
- `DATABASE_SCHEMA.md` defines the baseline relational model.
- `WORKFLOWS.md` describes query, ingestion, ACL, evaluation, and debugging flows.
- `POLICIES.md` defines security, RBAC, prompt-injection, logging, and operational policies.
- `TOOLS.md` lists expected local commands and CodeGraph usage.
- `SKILLS.md` routes local project and workflow skills.
- `MEMORY.md`, `PROJECT_STATUS.md`, `context/`, and `docs/adr/` capture project state, decisions, and open questions.
