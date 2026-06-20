# Milestone Gates

**Date**: 2026-06-19

This file documents the gate every milestone must pass before it
is allowed to advance. Gates are sequential per milestone. A
**Closed** status means the milestone has been authoritatively
completed and verified. A **Verified Ready** status means design
and verification package are complete and only the developer-
side verification commands are pending execution.

| Milestone | Gate name | Gate | Status |
|---|---|---|---|
| M0 | RBAC suite 100% pass | The pure function `decide(user, document)` passes the RBAC Access Outcome Suite. The function has zero framework imports. | Closed 2026-06-19 |
| M1 | Engineering remediation | Engineering findings are fixed (or documented as accepted for the owning milestone). Re-audit passes. Verification package documented. | Closed 2026-06-19 |
| M1 | Database round-trip verified | Migrations apply, rollback, re-apply. Indexes present. EXPLAIN check executed against the documents_access_filter_idx. Verification report shows status PENDING LOCAL EXECUTION until a developer or CI run reports PASS. | Closed 2026-06-19 (status PASSED) |
| M2 | Repository adapters round-trip | In-memory implementation behaves identically to the Postgres implementation for the operations listed in `PROJECT_STATUS.md` M2. | Closed 2026-06-20 (developer-side Postgres parity run on `localhost:55432`: 50 passed, 0 failed, 0 errors, 2 by-design skips; full combined pytest 81 passed, 2 skipped; see `docs/AUDITS/M2_REPORT.md` and findings F-24..F-28) |
| M3 | API Skeleton startup | `/health` returns 200; route surface is exactly `/health`, `/openapi.json`, `/docs`, `/redoc`. No retrieval, no generation, no DB, no JWT, no query-answer path. Launch contract `uvicorn src.api.app:create_app --factory`. | Verified Ready 2026-06-20 (working tree; combined pytest 44 passed and 52 dev-compose skips, M3 part 13/13 green in `tests/api/`) |
| M4 | Audit writer | Audit events flow from a stub use-case into `audit_logs` with `reason_code` and `correlation_id` populated. | Not started |
| M5 | JWT validation | Bad tokens return 401 and a `reason_code = JWT_INVALID` audit row. | Not started |
| M6 | LangGraph skeleton | The workflow state is typed with `user_id`, `department`, `clearance`, `role`, `correlation_id`. Anonymous execution impossible. | Not started |
| M7 | Ingestion idempotence | The same document content checksum re-applied leaves the document count unchanged. | Not started |
| M8 | Retrieval with access filter | Pre-retrieval SQL filter and post-rerank drop are present in tests. | Not started |
| M9 | Citation verification | Citations whose documents fail the access decision are dropped. | Not started |
| M10 | Regex Guard | Pattern-based refusals precede authorization and retrieval. | Not started |
| M11 | LLM Guard | The Guardrail Model is invoked and verdicts are recorded. | Not started |
| M12 | Audit and retrieval logs complete | `reason_code` and `candidate_counts` are populated. | Not started |
| M13 | RBAC suite 100% pass against full pipeline | The full RBAC Access Outcome Suite passes end to end. | Not started |
| M14 | Release gate blocks RBAC regression | The release gate runs both the RBAC and RAGAS suites; an RBAC regression fails the gate. | Not started |

Pass / fail status for any milestone is recorded under
`docs/HANDOFF/CURRENT_STATE.md`.
