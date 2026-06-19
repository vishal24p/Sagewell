# Sagewell

Repository name: `sagewell`

Sagewell is a single-company, single-tenant enterprise retrieval-augmented
generation (RAG) system. It answers questions over private organizational
documents using department and clearance as the only authorization
mechanism. Retrieval is hybrid (dense + BM25 + RRF fusion + cross-encoder
reranking). Workflow orchestration uses LangGraph. Document loading,
semantic chunking, ingestion, and retrieval abstractions use LlamaIndex.
The store is PostgreSQL with `pgvector` and `pg_search`. Evaluation is
RAGAS plus an RBAC Access Outcome Suite.

## V1 Scope

In scope:

- Single company, single tenant.
- Department + Clearance authorization only.
- Hybrid retrieval (Dense + BM25 + RRF + Cross-Encoder).
- LangGraph workflow orchestration.
- LlamaIndex for document loading, semantic chunking, ingestion, and
  retrieval abstractions.
- PostgreSQL with `pgvector` and `pg_search`.
- JWT authentication.
- Regex guard plus LLM guard on the primary request path. The
  Regex Guard runs after JWT validation and before RBAC and
  retrieval; the LLM Guard runs after retrieval and before
  generation.
- Citation verification.
- Incremental re-ingestion.
- RAGAS evaluation.
- RBAC Access Outcome Suite evaluation.

Out of scope for V1:

- Multi-tenant isolation.
- ACL engine, `document_acl` table, `permissions`/`role_permissions` tables.
- Groups, group memberships, group-based authorization.
- OIDC, Okta, Entra ID, LDAP, identity federation, external IAM.
- Permission resolution engines.
- Any authorization mechanism beyond department + clearance.

## Documentation

| File | Purpose |
|---|---|
| `AGENTS.md` | Agent constitution: how an agent must behave inside this repository. |
| `NEXT_AGENT.md` | Operational entry point: current milestone, current task, exit criteria. |
| `ARCHITECTURE.md` | System boundaries, components, retrieval pipeline, LangGraph responsibilities. |
| `DATABASE_SCHEMA.md` | V1 schema narrative. |
| `WORKFLOWS.md` | Runtime flows. |
| `POLICIES.md` | Security, authorization, prompt-protection, logging policies. |
| `TOOLS.md` | Local commands and tooling. |
| `SKILLS.md` | Local skill routing. |
| `MEMORY.md` | Authoritative decisions. |
| `PROJECT_STATUS.md` | V1 scope and the M0-M14 implementation roadmap. |
| `docs/HANDOFF/CURRENT_STATE.md` | Snapshot of repository progress (completed, in progress, not started). |
| `docs/HANDOFF/DECISIONS_PENDING.md` | Decisions that require human approval before implementation. |
| `docs/HANDOFF/KNOWN_ISSUES.md` | Unresolved engineering decisions (not bugs, not pending decisions). |
| `context/` | Project context (overview, requirements, decisions pointer, glossary). |
| `docs/adr/` | Architecture decision records. |
| `docs/AUDIT_REPORT.md` | Most recent documentation audit and corrections. |