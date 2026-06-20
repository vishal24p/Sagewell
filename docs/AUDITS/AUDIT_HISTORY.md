# Audit History

**Date**: 2026-06-19

This file records the audit passes applied to the Sagewell V1
repository. Each entry lists date, scope, method, and outcome.

| # | Date | Audit | Scope | Status |
|---|---|---|---|---|
| 1 | 2026-06-19 | Documentation alignment | `README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `WORKFLOWS.md`, `POLICIES.md`, `TOOLS.md`, `SKILLS.md`, `PROJECT_STATUS.md`, `MEMORY.md`, `context/*`, `docs/adr/*`, `skills/project/*` | report at `docs/AUDIT_REPORT.md` |
| 2 | 2026-06-19 | Architecture verification | The four primary files cross-checked against the approved V1 architecture | report at `docs/VERIFICATION_REPORT.md` |
| 3 | 2026-06-19 | M0 closure review | M0 deliverable: `src/domain/access/`, `tests/rbac/` | RBAC suite 31/31; status: closed |
| 4 | 2026-06-19 | M1 engineering pass | `migrations/`, `db/fixtures/`, `docker/`, `infrastructure/migrations/` | findings at `docs/AUDITS/FINDINGS.md`; remediation applied |
| 5 | 2026-06-19 | M1 remediation | Follow-up after the engineering pass; re-audit at `docs/AUDITS/M1_REMEDIATION_REPORT.md` | closed |
| 6 | 2026-06-19 | M1 Step A failure: image tag | dev compose | F-21 resolved: `paradedb/paradedb:pg17`; report at `docs/AUDITS/INVESTIGATION_REPORT_M1_IMAGE.md` |
| 7 | 2026-06-19 | M1 Step A failure: healthcheck escaping | dev compose healthcheck | F-22 resolved: `echo ... \| psql -tAX \| grep -q '^1$'` |
| 8 | 2026-06-19 | M1 Step B failure: host port collision | dev compose port mapping | F-23 resolved: 55432:5432 |
| 9 | 2026-06-19 | M1 closure | M1 review across findings F-21, F-22, F-23, all five HIGH gates, and the verification report status | M1 closed; report at `docs/AUDITS/M1_VERIFICATION_REPORT.md` (status PASSED) |
| 10 | 2026-06-20 | M2 architecture review | ports layer, in-memory and Postgres adapters, parity tests, RBAC suite preservation | review at this turn; findings produced `src/domain/ports/` value objects plus Protocols; ports layer co-located with entities |
| 11 | 2026-06-20 | M2 implementation | `src/infrastructure/repositories/{in_memory,postgres}/`, `tests/infrastructure/repositories/`, `pyproject.toml` dependency additions | RBAC Access Outcome Suite still 31/31; Postgres parity 52 skipped (sandbox cannot reach dev compose); M2 deliverable recorded at `docs/AUDITS/M2_REPORT.md` (initial) |
| 12 | 2026-06-20 | M2 developer-side parity run | ran pytest against `localhost:55432`; surfaced RC-1 (`SubRequest.param`), RC-2 (session-scoped pool under per-test loops), RC-3 (adversarial documents test) | F-24, F-25, F-26 recorded as RESOLVED; conftest and adversarial test reconciled via Re-1..Re-3 |
| 13 | 2026-06-20 | M2 parity re-run | applied F-27 (FK parent seed fixture) and F-28 (adversarial `Suite` test rewrite + production-side `isinstance(Suite)` validator hardening in both adapters) | M2 status flipped to Closed: 50 repository tests passed (in-memory + Postgres), 2 by-design skips, 0 failures, 0 errors; combined pytest 81 passed, 2 skipped |
| 14 | 2026-06-20 | M3 pre-implementation review | reduced M3 scope to pure API Skeleton per user; locked D-020..D-027; locked D-028 as forward hook | review captured in this session's plan and is reflected in `MEMORY.md` |
| 15 | 2026-06-20 | M3 implementation | `src/api/{app,__main__,settings}.py`, `src/api/middleware/correlation.py`, `src/api/errors/__init__.py`, `src/api/errors/schemas.py`, `src/api/routers/health.py`, `src/api/schemas/health.py`; `tests/api/` (5 files, 13 distinct tests), `pyproject.toml` add FastAPI/Pydantic/Uvicorn/Httpx, `docs/AUDITS/M3_REPORT.md`, `docs/HANDOFF/API_LOCAL_RUN.md` | M3 route surface is exactly `/health`, `/openapi.json`, `/docs`, `/redoc`. 13/13 API tests green; combined pytest 44 passed and 52 sandbox-skips, 0 failed. Drift mitigated inline: D-027 key rename to `exc_message` to dodge `LogRecord` reserved `message`; Starlette `ServerErrorMiddleware` re-raise consumed via `BaseHTTPMiddleware` wrapping. |
| 16 | 2026-06-20 | M3 closure and docs-alignment | M3 commit `fb110bd` (feat(M3)) pushed to `origin/main` (`c2a8ded..fb110bd`); closure-state corrections commit `b6125d9` (docs(M3 closure)) pushed to `origin/main`; pre-M4 docs alignment commit `debe101` (docs(pre-M4 cleanup)) pushed to `origin/main`. Branch is up to date with `origin/main`. | `docs/AUDITS/M3_REPORT.md`, `docs/AUDITS/MILESTONE_GATES.md`, `MEMORY.md`, `NEXT_AGENT.md`, `docs/HANDOFF/CURRENT_STATE.md` |

## Audit Process

Each audit follows the same shape:

- Date the work was performed.
- Scope: which files were inspected.
- Method: read end-to-end, cross-check against source of truth,
  identify findings.
- Status: which milestone or area the audit was scoped to.

Reminder of source-of-truth hierarchy: `ARCHITECTURE.md` first,
then `DATABASE_SCHEMA.md`, `POLICIES.md`, `WORKFLOWS.md`,
`docs/adr/`, `MEMORY.md`, summary files like `PROJECT_STATUS.md`,
operational files like `NEXT_AGENT.md` and `docs/HANDOFF/*`.

Adds new audit events at the top of the table. Old entries are
never deleted.
