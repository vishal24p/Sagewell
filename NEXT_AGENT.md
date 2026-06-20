# NEXT_AGENT

This file is the operational entry point for a new agent. It answers
one question: "what is the next task, and what do I need to know to
do it?"

Read `AGENTS.md` first. Read `docs/HANDOFF/CURRENT_STATE.md` for a
snapshot of progress. Read the files listed under "Relevant
Documents" before doing anything.

---

## Current Milestone

**M4 — Audit Infrastructure.**

## Current Status

**M0 closed on 2026-06-19 (commit `a78e21c`). M1 closed on
2026-06-19. M2 closed on `main` at `7849d89`. M3 closed on
`main` at `fb110bd` (pushed to `origin/main`).**

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

The current task is to flip this file (and the rest of the
operational handoff) to **M4 — Audit Infrastructure**.
Specifically:

- Introduce a real `AuditLogRepository` *writer* (the M2
  ports already declare its protocol; M4 makes the writer
  durable).
- Wire a correlation-id ingestion hook so that user-decision
  paths write durable `audit_logs` rows.
- Do NOT add `/v1/*` routes or any JWT/Auth coupling at
  M4. Those belong to M5.
- Do NOT add any retrieval/reranker coupling at M4. That
  belongs to M8.

### How to test (M4 prelude)

- `.venv\Scripts\python.exe -m pytest -q tests/api tests/rbac
  tests/infrastructure` is green.
- `grep -rE "fastapi|pydantic|uvicorn" src/domain/` returns
  zero rows.
- `grep -rE "asyncpg|psycopg|sqlalchemy|PersistenceError|
  ResourceNotFound|DomainError" src/api/` returns zero rows.

### How to verify before moving on to M5

- The M3 closure record at `docs/AUDITS/M3_REPORT.md` remains
  accurate.
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

## M3 Exit Criteria (CLOSED at `fb110bd`)

M3 was closed on 2026-06-20 with the commit `fb110bd`. All
twenty M3 exit criteria are documented in
`docs/AUDITS/M3_REPORT.md` with VERIFIED status. Re-running
the criteria should produce the same outcome — the
repository state is recorded in that report.

## M4-Do-Not-Touch (carry-forward from M0..M3)

The M0..M3 "Do Not Touch" lists still apply. Additions for M4
are NOT prohibitions against working on M4; they are
prohibitions against pre-empting M5+ while working on M4:

- Do NOT introduce JWT validation, even for testing — that
  belongs to M5.
- Do NOT introduce API-key auth, OAuth, or any non-JWT
  auth surface.
- Do NOT add `/v1/*` routes that proxy to retrieval, ranking,
  or generation. The audit writer at M4 owns the durable row;
  retrieval/ingress of `audit_events` is via the M2
  `AuditLogRepository` ports only.
- Do NOT add OpenAI/Anthropic/genai SDK dependency — wait
  for M11.
- Do NOT add prompt-protection guard (regex or LLM). That
  belongs to M10/M11.
- Do NOT add streaming or WebSocket — V1 stays request/response.
- Do NOT add CORS configuration beyond what the framework
  needs for the dev `/docs` and `/redoc` UIs.
- Do NOT introduce multi-tenant concepts, ACL tables, or
  group/role authorization. These are out of V1 per
  `AGENTS.md`.

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
 
