# Architecture Review Skill

Use this skill for architecture changes in Sagewell V1.

## Inputs

- `ARCHITECTURE.md`
- `WORKFLOWS.md`
- `POLICIES.md`
- Relevant ADRs in `docs/adr/`

## Checklist

- Authorization is department + clearance only. No ACL, no groups,
  no permissions, no role-based authorization, no external IAM.
- The access decision runs at three boundaries: pre-retrieval,
  post-rerank, citation verification.
- Retrieval is hybrid: dense + BM25 + RRF + cross-encoder. No
  vector-only or BM25-only retrieval. Reranking is mandatory.
- LangGraph handles workflow orchestration, state management, and
  node execution only. It does not handle authorization, retrieval,
  database access, or business logic.
- LlamaIndex handles document loading, semantic chunking, ingestion,
  and retrieval abstractions only. It does not handle authorization,
  workflow orchestration, or business rules.
- JWT validation runs on every request. Required claims include
  subject, department, clearance, expiration.
- Regex guard and LLM guard run on the primary request path. The
  Regex Guard runs after JWT validation and before RBAC and
  retrieval, so obvious prompt-injection attempts are refused
  before any authorization or retrieval work is performed. The LLM
  Guard runs after retrieval and before generation, so it can
  inspect the user query together with retrieved chunks for indirect
  prompt injection and retrieval-based attacks.
- Citation verification re-runs the access decision on every cited
  document.
- V1 tables only: users, documents, chunks, audit_logs,
  retrieval_logs, evaluation_results. Any new table requires an ADR.
- Models are capability-based. Generation Model, Embedding Model,
  Reranker Model, Guardrail Model. No specific model is pinned.
- Evaluation runs both RAGAS and the RBAC Access Outcome Suite.

## Done Condition

The review identifies boundary violations, missing access-decision
invocations, missing retrieval stages, prompt-protection gaps, model
pinning, table scope violations, and required ADR updates.