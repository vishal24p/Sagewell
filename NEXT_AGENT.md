# NEXT_AGENT

This file is the operational entry point for a new agent. It answers
one question: "what is the next task, and what do I need to know to
do it?"

Read `AGENTS.md` first. Read `docs/HANDOFF/CURRENT_STATE.md` for a
snapshot of progress. Read the files listed under "Relevant
Documents" before doing anything.

---

## Current Milestone

**M3 — API Skeleton (Reduced Scope).**

## Current Status

**M0 closed on 2026-06-19 (commit `a78e21c`). M1 closed on
2026-06-19. M2 closed on `main` at `7849d89`. M3 implementation
is complete in the working tree as of 2026-06-20; verification
is locally green (44 passed, 0 failed across the combined
api/rbac/infrastructure suites; remaining skips are M2
Postgres parity requiring the dev compose). M3 has not been
committed yet as of `LAST_UPDATED`.**

The M3 silhouette is the pure API skeleton per the user's
reduced-scope decision:

- `GET /health`
- `GET /openapi.json`
- `GET /docs`
- `GET /redoc`

**DB-NOTES**: `src/api/` does **not** import any DB driver
(`grep -rE "asyncpg|psycopg|sqlalchemy" src/api/` returns zero
rows). Future correlation router, audit writer, JWT validator,
and query-answer workflow all live in later milestones.

---

## Next Task

Commit M3 as a single milestone commit on `main`. Run the
verification gates listed under "M3 Exit Criteria". When
verification is complete, commit and append the M3 closure row
to `MEMORY.md`, `CURRENT_STATE.md`, `MILESTONE_GATES.md`,
`AUDIT_HISTORY.md`, and write `docs/AUDITS/M3_REPORT.md`.

After the commit lands, `NEXT_AGENT.md` flips to point at
M4. The M4 entry point is the Audit infrastructure
introduction: a real `AuditLogRepository` writer, a
correlation-id ingestion writer hook (no DB read inside the
correlation middleware), and the first durable audit-log row
on `user-auth-attempt` events.

### How to test (M3)

- `.venv\Scripts\python.exe -m pytest -q tests/api tests/rbac
  tests/infrastructure` is green (with the M2 Postgres parity
  half in skip until a developer-side Docker run).
- `grep -rE "fastapi|pydantic|uvicorn" src/domain/` returns
  zero rows.
- `grep -rE "asyncpg|psycopg|sqlalchemy|PersistenceError|
  ResourceNotFound|DomainError" src/api/` returns zero rows.

### How to verify before moving on to M4

- All M3 exit criteria listed in
  `docs/AUDITS/M3_REPORT.md` are checkstamped.
- Changes to the M3 boundary require an ADR (any new route or
  any new auth/audit coupling would trigger it).

---

## Relevant Documents

Read these before starting M4:

- `ARCHITECTURE.md` — layered boundaries; the audit writer
  layer lives inside `src/domain/ports/`.
- `DATABASE_SCHEMA.md` — V1 tables; `audit_logs` rows are the
  primary write target.
- `POLICIES.md` — IMM reason-code rules and the seven M0 reason
  codes.
- `WORKFLOWS.md` — the audit writer is invoked from M5 onward.
- `skills/project/database_design/SKILL.md` — schema and
  constraint invariants.

---

## Do Not Touch for M4

The M0..M3 "Do Not Touch" lists still apply. Additions for M4:

- OpenAI/Anthropic/genai SDK. Wait for M11.
- Prompt-protection guards (regex, LLM guard). Wait for M10/M11.
- Streaming responses / SSE / WebSocket. Out of V1.
- Any framework-only authentication provider (Okta, Entra,
  Auth0, OIDC). The V1 auth path is JWT-only.

## M3 Exit Criteria (carry-forward)

M3 is complete when **all** of the following are true:

1. `src/api/app.py` exports `def create_app() -> FastAPI` that
   returns a working app on import-test.
2. `uvicorn src.api.app:create_app --factory` boots without
   error.
3. `GET /health` returns 200 with body `{"status": "ok"}`.
4. `GET /openapi.json` returns 200; the document contains
   `paths["/health"]` and `components.schemas.HealthResponse`.
5. `GET /docs` returns 200 (HTML default UI).
6. `CorrelationIdMiddleware` echoes a user-supplied
   `X-Correlation-ID` and generates a UUID4 when missing.
7. Pydantic validation errors return 422 with the canonical
   error envelope (`code`, `message`, `correlation_id`).
8. An uncaught exception returns 500 with the canonical error
   envelope. The catch-all logs only the three keys mandated
   by D-027 (`correlation_id`, `exception_type`, `exc_message`).
9. No domain exception types are imported under `src/api/`.
10. No database driver imports appear under `src/api/`.
11. No JWT/Auth imports appear under `src/api/`.
12. `src/domain/` contains zero framework imports.
13. `pytest tests/api/` reports at least 13 distinct passing
    tests and zero failures.
14. M0 RBAC Access Outcome Suite still 31/31 green.
15. M2 parity suite still 50 passed / 2 by-design skips
    against the dev compose (skips OK when compose is absent).
16. M3 closure docs committed (`M3_REPORT.md`,
    `API_LOCAL_RUN.md`).
17. README lightweight note pointing to `API_LOCAL_RUN.md`.
18. Combined `pytest -q` reports `0 failed`.
19. Working tree clean of agent-authored scratch scripts.
20. AGENTS.md guardrails intact.

---

## Known Open Questions

The M0..M2 lists still apply unless resolved. M3 introduces:

- D-020 (Correlation generator algorithm): UUID4 confirmed.
  Carried over as durable decision.
- D-021 (Error envelope shape): fixed
  `{code, message, correlation_id}` for M3.
- D-024 (Settings surface): `SAGEWELL_LOG_LEVEL`,
  `SAGEWELL_API_HOST`, `SAGEWELL_API_PORT` only;
  `SAGEWELL_CORS_ALLOWED_ORIGINS` removed from M3.
- D-025 (Default docs surface): `/docs`, `/redoc`,
  `/openapi.json` enabled by default.
- D-026 (`__main__.py`): kept.
- D-027 (Catch-all log keys): `correlation_id`,
  `exception_type`, `exc_message` only (the third key is
  deliberately spelled `exc_message` to avoid colliding
  with the std-lib `LogRecord` reserved `message` field).
- D-028 (Forward hook): When the application surfaces a
  query-answer handler at M5/M6, it MUST NOT import any
  module under `src/api/`. The pattern is the inverted
  one: the api package depends on the workflow package,
  not the other way around.
 
