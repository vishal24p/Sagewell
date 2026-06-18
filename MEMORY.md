# Memory

This file records durable project decisions, assumptions, and open questions. Use ADRs for decisions with architectural consequences.

## Current Baseline

- Sagewell is a single-tenant Enterprise RAG system.
- Backend uses FastAPI with Clean Architecture.
- Workflow orchestration uses LangGraph.
- Ingestion and retrieval utilities use LlamaIndex.
- PostgreSQL is the primary datastore.
- `pgvector` stores embeddings.
- `pg_search` supports lexical and hybrid retrieval.
- Evaluation uses RAGAS plus custom RBAC evals.
- CodeGraph is initialized for the workspace.

## Accepted Decisions

| Date | Decision | Record |
|---|---|---|
| 2026-06-18 | Use a single-tenant Enterprise RAG baseline with RBAC, guardrails, hybrid retrieval, incremental ingestion, FastAPI, Clean Architecture, LangGraph, LlamaIndex, PostgreSQL, `pgvector`, `pg_search`, RAGAS, and custom RBAC evals. | `docs/adr/0001-single-tenant-enterprise-rag-baseline.md` |
| 2026-06-18 | Keep `AGENTS.md` as behavior and pointers only. Put architecture, schema, workflows, policies, tools, and skill routing in separate documents. | This file |
| 2026-06-18 | Route agents to local repo skills first: `skills/project/` for project skills and `skills/external/` for vendored external skills. Do not depend on outside installed skill paths for this project. | `SKILLS.md` |
| 2026-06-18 | Name the project Sagewell and document the intended GitHub repository name as `sagewell`. Do not rename the local workspace directory. | `README.md` |

## Assumptions

- Tenant isolation is deployment-level because the project is single tenant.
- Internal users still have different access levels, so RBAC remains mandatory.
- Documents may contain hostile or misleading instructions.
- Source implementation has not started in this scaffold.
- A future implementation will add concrete migration, test, and deployment commands.

## Open Questions

- Which identity provider will be used for authentication?
- Are document ACLs imported from source systems, managed locally, or both?
- Which embedding model and reranker will be approved for production?
- What document connectors are in first scope?
- What data retention policy applies to prompts, answers, traces, and audit logs?
- What latency and cost targets should retrieval and generation meet?
- Will deployment run in containers, managed app services, or another platform?

## Update Rules

- Add concise entries when a decision affects future implementation.
- Move architectural decisions into `docs/adr/` when alternatives and consequences matter.
- Do not store secrets, credentials, or private customer data here.
