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
| 17 | 2026-06-20 | M4 commit + push to `origin/main` | one milestone commit `03351c4` on `main`; 20 files changed (+845/-26). 10/10 use-case tests green; combined pytest 54 passed, 52 sandbox-skips, 0 failed. M0 RBAC still 31/31, M3 tests/api still 13/13. Launch contract `uvicorn src.api.app:create_app --factory` continues to boot without a database; the factory accepts an optional `audit_repo` for runtime wiring. Pushed via `git push origin main` (`debe101..03351c4`). Branch is up to date with `origin/main`. | `docs/AUDITS/M4_REPORT.md`, `docs/HANDOFF/API_LOCAL_RUN.md` |
| 18 | 2026-06-21 | M5 commit on `rag-langgraph` | `src/application/auth/` (VerifyJwtToken use case, HS256 signer, typed-actor projection, typed-failure hierarchy), `src/api/middleware/auth.py` (pure-ASGI JWT middleware), `__main__` reads `SAGEWELL_JWT_SECRET` and constructs `HS256JwtSigner`, `create_app(jwt_signer=...)` DI seam; 19 new tests in `tests/api/` (10 application + 6 middleware + 3 existing reused) and 10 in `tests/application/auth/`; combined pytest 73 passed, 52 sandbox-skips, 0 failed. Bug-fix surface recorded in F-31..F-34. Closure report at `docs/AUDITS/M5_REPORT.md`. Branch is `rag-langgraph`; the next advisory step reviews whether to fast-forward `main`. | `docs/AUDITS/M5_REPORT.md`, `docs/AUDITS/FINDINGS.md` (F-31..F-34) |
| 19 | 2026-06-21 | M6 commit on feature branch | `src/application/workflow/` (frozen `WorkflowState` dataclass, `from_actor` factory, typed-failure hierarchy), `src/infrastructure/langgraph/workflow.py` (channel/state adapter, skeleton graph, async `run_workflow`). pyproject adds `langgraph>=0.4,<0.6`. 13 new tests across `tests/application/workflow` and `tests/infrastructure/langgraph`. Combined pytest 86 passed (was 73), 52 sandbox-skips, 0 failed. M0 RBAC still 31/31; M3 tests/api still 13/13; M4 tests/application/audit_event still 10/10; M5 tests/application/auth still 10/10; M5 tests/api still 19/19. The M3/M5 API route surface is unchanged; no `/v1/*` endpoint lands at M6 (per `PROJECT_STATUS.md`). Closure report at `docs/AUDITS/M6_REPORT.md`. Branch `feat/m6-langgraph-skeleton`; `main` and `feat/m5-jwt-validation` are untouched. | `docs/AUDITS/M6_REPORT.md`, `docs/AUDITS/FINDINGS.md` (F-35) |
| 20 | 2026-06-26 | M7 commit on feature branch | `src/application/ingestion/` (IngestDocument use case, IngestDocumentCommand / IngestDocumentResult / IngestOutcome, typed-error hierarchy, normalize_content_checksum helper), `src/domain/ports/ingestion.py` (DocumentChunkerProtocol, EmbeddingModelProtocol, ChunkSegment), `src/infrastructure/ingestion/{chunker,embedding}.py` (LlamaIndexChunker + deterministic-hash embedder adapter). Documentation widens: DocumentRepository.upsert_by_source + ChunkRepository.replace_for_document (M7 write methods on existing M2 ports); reason_codes widens with three ingestion outcome codes. pyproject adds `llama-index-core>=0.13,<0.15`. 15 new tests across tests/application/ingestion (6), tests/infrastructure/ingestion (4), tests/infrastructure/repositories/test_documents_m7_upsert.py (5). Combined pytest 101 passed (was 86 at M6; net +15), 52 sandbox-skips, 0 failed. M0 RBAC still 31/31; M3 tests/api still 13/13; M4 tests/application/audit_event still 10/10; M5 tests/application/auth still 10/10; M6 tests/application/workflow still 8/8; M6 tests/infrastructure/langgraph still 5/5. The M3/M5/M6 API route surface is unchanged at M7; no `/v1/*` endpoint lands here. Closure report at `docs/AUDITS/M7_REPORT.md`; findings F-36 (capability-deferred embedding stub), F-37 (predicate-vs-Literal reason-code widening), F-38 (typed-error slug defaults) added. Branch `feat/m7-ingestion`; `main`, `feat/m5-jwt-validation`, `feat/m6-langgraph-skeleton` untouched. | `docs/AUDITS/M7_REPORT.md`, `docs/AUDITS/FINDINGS.md` (F-36..F-38) |

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
