# Project Overview

Sagewell is a single-tenant enterprise retrieval-augmented generation system. It is designed for controlled access to private organizational knowledge, not open public search.

## Baseline

- FastAPI backend.
- Clean Architecture.
- LangGraph workflow orchestration.
- LlamaIndex ingestion and retrieval utilities.
- PostgreSQL primary database.
- `pgvector` for embeddings.
- `pg_search` for lexical and hybrid retrieval.
- RBAC enforcement across retrieval and answer generation.
- Prompt-injection guardrails.
- Incremental ingestion.
- RAGAS and custom RBAC evals.

## Success Criteria

- A user can only retrieve and cite content they are allowed to access.
- Ingestion can update changed documents without rebuilding everything.
- Retrieval combines semantic and lexical matching.
- Answers include verifiable citations.
- Prompt-injection attempts inside documents do not override system policy.
- Evaluation catches access-control and retrieval regressions.

## Primary Users

- Enterprise employees asking questions over internal documents.
- Knowledge admins managing sources and ACLs.
- Engineers operating ingestion, retrieval, and evaluation.
- Security reviewers auditing access behavior.
