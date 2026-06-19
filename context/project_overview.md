# Project Overview

Sagewell is a single-company, single-tenant enterprise RAG system. It
answers questions over private organizational documents using
department and clearance as the only authorization mechanism.

## Baseline

- API layer with JWT authentication.
- Authorization: department + clearance only.
- Retrieval: dense + BM25 + RRF + cross-encoder reranking.
- Workflow orchestration: LangGraph.
- Document loading, semantic chunking, ingestion, retrieval
  abstractions: LlamaIndex.
- Data store: PostgreSQL with `pgvector` and `pg_search`.
- Prompt protection: regex guard and LLM guard on the primary request
  path.
- Evaluation: RAGAS and the RBAC Access Outcome Suite (both
  required).
- Models: capability-based. Generation Model, Embedding Model,
  Reranker Model, Guardrail Model.

## Success Criteria

- An actor can only retrieve and cite content the access decision
  permits.
- Ingestion updates changed documents without rebuilding everything.
- Retrieval combines dense and BM25 signals with reranking.
- Answers include verifiable citations.
- Regex and LLM guards run on the primary request path.
- Prompt-injection attempts in documents do not override system
  policy.
- RAGAS and the RBAC Access Outcome Suite both run on every release
  gate.

## Primary Users

- Enterprise employees asking questions over internal documents.
- Knowledge admins managing sources.
- Engineers operating ingestion, retrieval, and evaluation.
- Security reviewers auditing access behavior.

## V1 Out of Scope

- Multi-tenant isolation.
- ACL engine, `document_acl`, permissions, role_permissions.
- Groups and group-based authorization.
- OIDC, Okta, Entra ID, LDAP, identity federation, external IAM.
- Permission resolution engines.