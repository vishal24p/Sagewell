# Project Status

**Date**: 2026-06-26

## State

**V1 implementation complete.** All milestones M0..M14 closed on a series of feature branches, all pushed to `origin` (verified via `git ls-remote --heads origin`). **M15** (real-corpus end-to-end pipeline test) closed on `feat/m15-real-corpus` on top of V1 - exercises M7 ingestion → M8 retrieval → M9 citation-verification against the on-disk `en/` corpus (kubernetes/website English localization tree, ~3386 markdown files / 84.64 MB). The corpus directory is intentionally NOT pushed; `.gitignore` preserves the rule. M15 does not change architecture, schema, or workflow-state shape; it exercises what V1 already shipped.

- M0 (RBAC pure function) - closed 2026-06-19 on `main` (`a78e21c`).
- M1 (Engineering remediation + migrations + indexes) - closed 2026-06-19 on `main`.
- M2 (Repository adapters) - closed 2026-06-20 on `main` (`7849d89`). Developer-side Postgres parity run green.
- M3 (API Skeleton) - closed 2026-06-20 on `main` (`fb110bd`).
- M4 (Audit Writer) - closed 2026-06-20 on `main` (`03351c4`).
- M5 (JWT validation) - closed 2026-06-21 on `feat/m5-jwt-validation`.
- M6 (LangGraph Skeleton) - closed 2026-06-21 on `feat/m6-langgraph-skeleton`.
- M7 (Ingestion) - closed 2026-06-26 on `feat/m7-ingestion`. Follow-up commit `ce0c645` fixes the SKIPPED-as-ALLOWED decision.
- M8 (Retrieval with Access Filter) - closed 2026-06-26 on `feat/m8-retrieval`.
- M9 (Workflow Wiring with Citations) - closed 2026-06-26 on `feat/m9-workflow-citations`.
- M10 (Regex Guard) - closed 2026-06-26 on `feat/m10-regex-guard`.
- M11 (LLM Guard capability port, D-004) - closed 2026-06-26 on `feat/m11-llm-guard`.
- M12 (Audit + Retrieval Logs complete) - closed 2026-06-26 on `feat/m12-logs-complete`.
- M13 (RAGAS capability port, D-006) - closed 2026-06-26 on `feat/m13-ragas`.
- M14 (End-to-end Hardening + Release Gate) - closed 2026-06-26 on `feat/m14-hardening`.
- **M15 (Real-Corpus End-to-End Pipeline Test)** - closed 2026-06-27 on `feat/m15-real-corpus`. Real-corpus pipeline test exercising M7→M8→M9 against the on-disk `en/` corpus.

Combined pytest: **195 passed, 52 sandbox-skips, 0 failed**. Release-gate test surface: `tests/release_gate/` (launch-contract + envelope + M10-refusal + full-stack-smoke + end-to-end RBAC Access Outcome Suite + M15 real-corpus pipeline). The launch contract boots DB-free end-to-end on `uvicorn src.api.app:create_app --factory`.

Documentation is aligned to the approved V1 architecture. Open questions D-001..D-006 (JWT readiness / Embedding Model / Reranker Model / Guardrail Model / Generation Model / RAGAS SDK) own their own out-of-V1 adoption milestones; each requires its own ADR per `docs/HANDOFF/DECISIONS_PENDING.md`.

Documentation is aligned to the approved V1 architecture.

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

- Source implementation exists at M0..M7 on `main` and feature
  branches. Model capabilities (Embedding, Reranker, Guardrail,
  Generation) remain capability-based until separate ADRs are
  written.
- `pg_search` extension name and version are not pinned.
- `skills/external/accessibility/SKILL.md` is not present; UI
  accessibility work must report that missing local route before
  falling back to outside installed guidance.
- M5 architecture decision D-001 locks HS256-only at M5. RS256
  or JWKS would require an ADR; the JWKS plan from
  `DECISIONS_PENDING.md` is the canonical next step.
- M6 ships an empty LangGraph state machine under
  `src/infrastructure/langgraph/workflow.py`. The `noop_node`
  round-trips the typed `WorkflowState` and returns identity.
  Future milestones (M7-M9) replace the noop with retrieval,
  rerank, generation, and the access-decision boundaries.
- M7 ships the placeholder deterministic-hash embedder; the
  Embedding Model capability is decision-deferred per open
  question D-002. The LlamaIndex `SentenceSplitter` adapter
  ships at M7; production-grade embeddings land at the milestone
  that adopts the Embedding Model capability. M7 introduces
  zero `/v1/...` endpoints; the use case is exercised through
  tests. The launch contract stays DB-free at M7.

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
4. M3 — API Skeleton. FastAPI app factory, correlation-ID
   middleware, error envelope translation layer, settings,
   `GET /health`, `/openapi.json`, `/docs`, `/redoc`.
   Standalone — no DB, no JWT, no query-answer endpoint, no
   audit/correlation lookup. Launch via
   `uvicorn src.api.app:create_app --factory`.
5. M4 — Audit Infrastructure. Application-layer audit-intake
   use case under `src/application/audit_event/`. The use
   case class `RecordAuditEvent` calls the M2 `AuditLogRepository.append()`
   port; the seven M0 IMM reason codes are stable. The
   use case is exercised through tests; the launch contract
   stays DB-free until M5. M4 ships no middleware and no
   `/v1/*` routes.
6. M5 — JWT Validation. The auth application package
   (`src/application/auth/`) owns the `VerifyJwtToken`
   use case and the typed-actor projection
   `{user_id, department, clearance, role, correlation_id}`.
   A real FastAPI middleware at the API boundary calls
   `VerifyJwtToken` on every request. HS256-only signer
   (D-001); no JWKS at M5. Bad/missing/bad-signature tokens
   return 401 with the canonical error envelope and a
   `record_audit_event` row carrying
   `reason_code = JWT_INVALID` (through M4). The launch
   contract stays DB-free: `create_app(audit_repo=None)`
   still boots. Tests run against the application package
   without requiring a DB.
7. M6 — LangGraph Skeleton. A runnable, empty state machine, actor-
   aware. The state object is typed with `user_id`, `department`,
   `clearance`, `role`, and `correlation_id` from the first test.
   The workflow refuses to start if any of these fields are missing
   (anonymous execution is impossible). The M6 milestone ships the
   empty skeleton (`START -> noop_node -> END`) and **does NOT**
   mount a `/v1/*` endpoint onto the workflow. The endpoint lands at
   the milestone that wires the V1 retrieval / guards / generation
   pipeline (per the implementation sequencing below).
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