# Project Status

**Date**: 2026-06-19

## State

Documentation is aligned to the approved V1 architecture. Source
implementation files are not present yet.

## V1 Scope

In scope:

- Single-company, single-tenant Enterprise RAG.
- Department + Clearance authorization only.
- Hybrid retrieval: dense + BM25 + RRF + cross-encoder reranking.
- LangGraph workflow orchestration.
- LlamaIndex for document loading, semantic chunking, ingestion, and
  retrieval abstractions.
- JWT authentication.
- Regex guard and LLM guard on the primary request path.
- Citation verification.
- Incremental re-ingestion.
- PostgreSQL with `pgvector` and `pg_search`.
- RAGAS evaluation.
- RBAC Access Outcome Suite evaluation.

Out of scope for V1:

- Multi-tenant isolation.
- ACL engine, `document_acl`, permissions, role_permissions.
- Groups and group-based authorization.
- OIDC, Okta, Entra ID, LDAP, identity federation, external IAM.
- Permission resolution engines.
- Code implementation.
- Dependency installation.
- Network calls.
- Deployment provisioning.
- UI design.

## Completed In Documentation

- Architecture aligned to V1 (LangGraph, LlamaIndex, hybrid retrieval,
  capability-based models, JWT, regex guard, LLM guard).
- Database schema narrowed to V1 tables only.
- Policies rewritten to department + clearance only.
- Workflows rewritten around the V1 retrieval and guard pipeline.
- Skills narrowed to V1 scope (no ACL/groups/OIDC language).
- Project skills (architecture_review, database_design, debugging,
  evaluation, ingestion_pipeline, rbac, retrieval_engine) rewritten
  to V1 scope.
- Documentation audit recorded at `docs/AUDIT_REPORT.md`.

## Current Risks

- No source implementation exists, so there is no executed access
  decision to compare against the policy.
- Model capabilities (Embedding, Reranker, Guardrail, Generation) are
  not pinned. They remain capability-based until separate ADRs are
  written.
- `pg_search` extension name and version are not pinned.
- `skills/external/accessibility/SKILL.md` is not present; UI
  accessibility work must report that missing local route before
  falling back to outside installed guidance.

## Next Implementation Milestones

The build order is fixed by dependencies and optimized for
debuggability, isolation, testability, architectural correctness, and
risk reduction. Speed of development is not a goal. No component is
introduced until all of its dependencies are validated.

1. M0 — Access Decision (pure). Build the access decision as a pure
   function. Wire the RBAC Access Outcome Suite against it.
2. M1 — Schema, Migrations, Fixtures, Indexes. Lock the data
   contract. Migrations apply and roll back. Indexes (`pgvector` HNSW,
   `pg_search` GIN, B-tree on `documents(department,
   required_clearance, status)`) are present. EXPLAIN check passes.
3. M2 — Repositories. In-memory first, real PostgreSQL second.
   Every operation used by later phases has a passing test.
4. M3 — API Skeleton. FastAPI startup, `/health`, `/query` stub,
   correlation ID middleware, error translation. No retrieval, no
   workflow, no generation.
5. M4 — Audit Infrastructure. Correlation ID helper, audit writer
   interface, basic audit event persistence. Builds on the repositories.
6. M5 — JWT Validation. Validate the JWT, build the actor-loading
   path (`user_id`, `department`, `clearance`, `role`), and provide
   the actor as the canonical input to the workflow state. 401 on
   missing/expired/bad-signature tokens. `audit_logs` row with
   `reason_code = JWT_INVALID` on every failure.
7. M6 — LangGraph Skeleton. A runnable, empty state machine, actor-
   aware. The state object is typed with `user_id`, `department`,
   `clearance`, `role`, and `correlation_id` from the first test.
   The workflow refuses to start if any of these fields are missing
   (anonymous execution is impossible). The API at M3 invokes the
   workflow with a JWT-derived actor.
8. M7 — Ingestion. LlamaIndex loads, semantic-chunks, and embeds
   documents. Idempotent on `documents.content_checksum`. Replaced
   chunks are not searchable. Job outcome is written to `audit_logs`.
9. M8 — Retrieval with Access Filter. The four stages (Dense, BM25,
   RRF, Cross-Encoder) are developed one at a time. Each stage is
   paired with the access decision from the first test. There is no
   milestone where retrieval works without access enforcement. The
   pre-retrieval SQL filter and the post-rerank drop are exercised as
   part of this phase, not as a separate phase.
10. M9 — Workflow Wiring with Citations. The workflow at M6 is wired
    to the access-decision-filtered retrieval at M8. The third
    access-decision boundary (citation re-run) is exercised on a typed
    candidate-citation list produced by stub generation. Citations
    whose documents fail the access decision are dropped. If all
    candidate citations fail, the answer is refused.
11. M10 — Regex Guard. Pattern-based detection on the normalized
    query. Runs after JWT validation and before RBAC. Pattern set is
    versioned. Refused requests do not consume authorization or
    retrieval work.
12. M11 — LLM Guard. The Guardrail Model classifies the (query,
    retrieved chunks) pair. Runs after retrieval and before
    generation. Verdict and rationale recorded in `audit_logs`.
13. M12 — Audit and Retrieval Logs (complete). Do-not-log enforcement,
    full reason-code enum, retrieval-log writer with candidate counts.
    Builds on the M4 audit infrastructure.
14. M13 — RAGAS Evaluation. RAGAS cases run the full pipeline and
    record scores in `evaluation_results`. The release gate runs both
    the RBAC Access Outcome Suite and the RAGAS suite and blocks on
    RBAC regression.
15. M14 — End-to-end Hardening. Failure paths (401, 403, 503,
    refusal, audit-write-failure, retrieval-empty, citation-fail),
    performance, observability, and the release gate in CI.

Implementation sequencing note: JWT validation is introduced before
the LangGraph skeleton so that the workflow state is designed
around an authenticated actor from the first test. The workflow
should never be designed around anonymous execution and later
adapted to authenticated execution. From the LangGraph phase onward,
the workflow state contains `user_id`, `department`, `clearance`,
`role`, and `correlation_id`.