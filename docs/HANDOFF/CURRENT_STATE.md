# Current State

**Last updated**: 2026-06-19

This file is a snapshot of repository progress. It is operational,
not authoritative. For architecture, see `ARCHITECTURE.md`. For the
implementation roadmap, see `PROJECT_STATUS.md`. For pending
decisions, see `docs/HANDOFF/DECISIONS_PENDING.md`. For unresolved
engineering concerns, see `docs/HANDOFF/KNOWN_ISSUES.md`.

---

## Current Architecture Version

Architecture version: **V1**.

Source of truth: `docs/adr/0001-single-tenant-enterprise-rag-baseline.md`.

Key invariants of V1:

- Single-company, single-tenant Enterprise RAG.
- Authorization: department + clearance only.
- Retrieval: dense + BM25 + RRF + cross-encoder reranking.
- Workflow orchestration: LangGraph.
- Document loading, semantic chunking, ingestion, retrieval
  abstractions: LlamaIndex.
- Data store: PostgreSQL with `pgvector` and `pg_search`.
- Authentication: JWT.
- Prompt protection: regex guard and LLM guard on the primary
  request path. Regex Guard runs before RBAC and retrieval.
- Evaluation: RAGAS and the RBAC Access Outcome Suite (both
  required).
- Models: capability-based.
- V1 tables: `users`, `documents`, `chunks`, `audit_logs`,
  `retrieval_logs`, `evaluation_results`.

---

## Current Milestone

**M0 — Access Decision (pure).**

Full milestone list: `PROJECT_STATUS.md` (M0-M14).

---

## Completed

| Milestone | Description | Date |
|---|---|---|
| (none) | No source code or tests exist yet. | — |

### Completed In Documentation

| Item | Date |
|---|---|
| V1 architecture approved (`docs/adr/0001-...`) | 2026-06-19 |
| Documentation audit and corrections (`docs/AUDIT_REPORT.md`) | 2026-06-19 |
| Architecture verification pass (`docs/VERIFICATION_REPORT.md`) | 2026-06-19 |
| Implementation roadmap published (`PROJECT_STATUS.md` M0-M14) | 2026-06-19 |
| Roadmap refinement: JWT before LangGraph skeleton | 2026-06-19 |
| Agent-handoff refactor: `AGENTS.md` reduced to constitution, `NEXT_AGENT.md` and `docs/HANDOFF/` created | 2026-06-19 |

---

## In Progress

| Milestone | Description | Owner | Started |
|---|---|---|---|
| M0 | Access Decision (pure). | (none assigned) | (not started) |

---

## Not Started

| Milestone | Description |
|---|---|
| M1 | Schema, Migrations, Fixtures, Indexes. |
| M2 | Repositories. |
| M3 | API Skeleton. |
| M4 | Audit Infrastructure. |
| M5 | JWT Validation. |
| M6 | LangGraph Skeleton (actor-aware). |
| M7 | Ingestion. |
| M8 | Retrieval with Access Filter. |
| M9 | Workflow Wiring with Citations. |
| M10 | Regex Guard. |
| M11 | LLM Guard. |
| M12 | Audit and Retrieval Logs (complete). |
| M13 | RAGAS Evaluation. |
| M14 | End-to-end Hardening. |

---

## Recently Decided

| Date | Decision |
|---|---|
| 2026-06-19 | V1 architecture baseline accepted. |
| 2026-06-19 | `MEMORY.md` is the authoritative decisions log. `context/decisions.md` is a pointer. |
| 2026-06-19 | Local skills are the source of routing. `skills/project/` for project skills, `skills/external/` for vendored external skills. |
| 2026-06-19 | Project name is Sagewell. Intended GitHub repository name is `sagewell`. |
| 2026-06-19 | V1 implementation sequencing: JWT before LangGraph skeleton. Workflow state typed with `user_id`, `department`, `clearance`, `role`, `correlation_id` from the first test. |
| 2026-06-19 | Agent-handoff architecture: `AGENTS.md` is the constitution. `NEXT_AGENT.md` carries operational state. `docs/HANDOFF/` carries progress, pending decisions, and known issues. |

---

## Known Risks

- No source implementation exists yet. There is no executed access
  decision to compare against the policy. Until M0 lands, the
  architecture is provable on paper only.
- Model capabilities (Embedding, Reranker, Guardrail, Generation)
  are not pinned. They remain capability-based until separate ADRs
  are written.
- `pg_search` extension name and version are not pinned.
- `skills/external/accessibility/SKILL.md` is not present; UI
  accessibility work must report that missing local route before
  falling back to outside installed guidance.
- RAGAS and RBAC release-gate thresholds are not pinned.

---

## Update Rule

Update this file when a milestone starts, completes, or blocks.
Keep entries concise. Do not duplicate the milestone descriptions
that already live in `PROJECT_STATUS.md`.