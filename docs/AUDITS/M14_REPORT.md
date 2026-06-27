# M14 Closure - End-to-end Hardening

**Date**: 2026-06-26
**Milestone**: M14 - End-to-end Hardening + Release Gate.
**Scope**: M14 ships the release-gate test suite that pins the launch contract boots DB-free, the M9 pipeline envelope is correct on benign queries, the M10 Regex Guard refusal flows through the gate, and the M0 RBAC Access Outcome Suite runs end-to-end through the M9 pipeline (the D-007 100% pass bar).
**Status**: CLOSED 2026-06-26 on feat/m14-hardening.

---

## Decision IDs Locked

| D-ID | Decision |
|---|---|
| D-090 | M14 ships tests/release_gate/test_m14_hardening.py with five release-gate tests: launch contract DB-free boots, /v1/query returns 503 when run_query is not wired, end-to-end /v1/query envelope through a stub runner, M10 Regex Guard refusal observed by the release gate, full M5+M8+M9+M10+M11 stack smoke wires. |
| D-091 | M14 ships tests/release_gate/test_m14_rbac_suite.py with seven RBAC suite integration tests through the M9 pipeline: pre-filter projection surfaces, clearance_insufficient / department_mismatch / missing_user_clearance fail-closed, citation verification drops mismatched-document citations, citation verification drops missing-document citations fail-closed, citation verification drops clearance-insufficient citations. |
| D-092 | The release gate is the combined pytest result; 100% pass on M0 RBAC + M14 release-gate is the canonical release bar. The launch contract boots DB-free end-to-end on uvicorn src.api.app:create_app --factory (no audit_repo, no run_query, no regex_guard). |

## Files Created

- tests/release_gate/__init__.py
- tests/release_gate/test_m14_hardening.py -- 5 tests.
- tests/release_gate/test_m14_rbac_suite.py -- 7 tests.

## Verification

Combined pytest 166 passed, 52 skipped, 0 failed (was 154 at M13 closure; net +12 from M14).

## Final V1 Status

V1 implementation M0 -> M1 -> M2 -> M3 -> M4 -> M5 -> M6 -> M7 -> M8 -> M9 -> M10 -> M11 -> M12 -> M13 -> M14 is COMPLETE.

| Min | Description | Pytest baseline (cumulative) | Branch |
|---|---|---|---|
| M0 | Access decision (pure) | 31 | a78e21c on main |
| M1 | Schema, migrations, fixtures, indexes | + verified | main |
| M2 | Repositories (ports + in-memory + Postgres) | 81 (50+31 RBAC), skip 2 | 7849d89 on main |
| M3 | API Skeleton (reduced scope) | 44 + RBAC + sandbox-skips | fb110bd on main |
| M4 | Audit writer | 54 + sandbox-skips | 03351c4 on main |
| M5 | JWT validation (HS256) | 73 + sandbox-skips | feat/m5-jwt-validation |
| M6 | LangGraph skeleton (actor-aware) | 86 + sandbox-skips | feat/m6-langgraph-skeleton |
| M7 | Ingestion (LlamaIndex, idempotent) | 101 + sandbox-skips | feat/m7-ingestion |
| M7 FU | SKIPPED audit-row decision is ALLOWED | 103 + sandbox-skips | feat/m7-ingestion |
| M8 | Retrieval with Access Filter | 118 + sandbox-skips | feat/m8-retrieval |
| M9 | Workflow Wiring with Citations | 130 + sandbox-skips | feat/m9-workflow-citations |
| M10 | Regex Guard | 137 + sandbox-skips | feat/m10-regex-guard |
| M11 | LLM Guard (capability port) | 142 + sandbox-skips | feat/m11-llm-guard |
| M12 | Audit + Retrieval Logs complete | 148 + sandbox-skips | feat/m12-logs-complete |
| M13 | RAGAS Evaluation (capability port) | 154 + sandbox-skips | feat/m13-ragas |
| M14 | End-to-end Hardening + Release Gate | 166 + sandbox-skips | feat/m14-hardening |

V1 is release-ready from the M0 -> M14 milestones' standpoint. The launch contract remains DB-free end-to-end (no asyncpg, no pg_search SDK, no LlamaIndex SDK, no hosted model SDKs in the application / workflow packages). The capability-deferred model SDKs (Embedding, Reranker, Generation, Guardrail, RAGAS) are typed via Protocol ports; the production adoptions land at their owning milestones per open questions D-002..D-006.
