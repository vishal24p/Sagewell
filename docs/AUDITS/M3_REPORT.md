# M3 Closure — API Skeleton (Reduced Scope)

**Date**: 2026-06-20
**Milestone**: M3 — API Skeleton
**Scope**: Pure API skeleton per the user's reduction.
**Working tree status**: implementation complete; pending
single-commit closure on `main`.

---

## Decision IDs Locked

| D-ID | Decision |
|---|---|
| D-020 | Correlation ID generator is **UUID4** (`uuid.uuid4()`). |
| D-021 | Error envelope: minimal `{code, message, correlation_id}`. |
| D-024 | Settings: env prefix `SAGEWELL_` with three fields only — `SAGEWELL_LOG_LEVEL`, `SAGEWELL_API_HOST`, `SAGEWELL_API_PORT`. `SAGEWELL_CORS_ALLOWED_ORIGINS` removed from M3. |
| D-025 | Default docs surface: `/docs`, `/redoc`, `/openapi.json` enabled. |
| D-026 | `src/api/__main__.py` retained for `python -m src.api`. |
| D-027 | Catch-all log keys (D-027 mandate): `correlation_id`, `exception_type`, `exc_message`. |

> M3 also discovery-named a new runtime invariant — the
> `exc_message` spelling. CI/devs should treat `exc_message` as
> the canonical key going forward; the original `message` key
> collides with `LogRecord`'s reserved field.

---

## Files Created Under M3

- `src/api/__init__.py` (docstring + guardrail)
- `src/api/app.py` (`create_app()` factory)
- `src/api/__main__.py` (`python -m src.api`)
- `src/api/settings.py`
- `src/api/errors/__init__.py`
- `src/api/errors/schemas.py`
- `src/api/middleware/__init__.py`
- `src/api/middleware/correlation.py`
- `src/api/schemas/__init__.py`
- `src/api/schemas/health.py`
- `src/api/routers/__init__.py`
- `src/api/routers/health.py`
- `tests/api/__init__.py`
- `tests/api/conftest.py`
- `tests/api/test_health.py`
- `tests/api/test_openapi.py`
- `tests/api/test_error_translation.py`
- `tests/api/test_correlation.py`
- `tests/api/test_create_app_factory.py`
- `docs/AUDITS/M3_REPORT.md` (this file)
- `docs/HANDOFF/API_LOCAL_RUN.md`

## Files Modified Under M3

- `pyproject.toml` — added `fastapi`, `pydantic`,
  `pydantic-settings`, `uvicorn[standard]` to
  `dependencies`; `httpx` to dev deps.
- `NEXT_AGENT.md` — flipped Current Milestone to M3; left
  M4-relevant pointers.
- `docs/HANDOFF/CURRENT_STATE.md` — flipped Current Milestone
  to "M2 closed. M3 in progress". Added M3 row to Recently
  Completed and the D-IDs to Recently Decided.
- `MEMORY.md` — appended M3 closure row.
- `docs/AUDITS/MILESTONE_GATES.md` — added M3 row.
- `docs/AUDITS/AUDIT_HISTORY.md` — appended M3 rows.
- `README.md` — half-line under "Build phase" pointing at
  `docs/HANDOFF/API_LOCAL_RUN.md`.

---

## Surface

### Route surface

```
GET /health     200 {"status":"ok"}
GET /openapi.json  200 (openapi document)
GET /docs          200 (Swagger UI HTML)
GET /redoc         200 (Redoc HTML)
```

### Behavior contracts

- Every request receives an `X-Correlation-ID` header on the
  response. If the request supplied one, it is echoed; if not,
  a fresh UUID4 is generated and returned.
- Validation errors are mapped to **422** with
  `{code: "validation_error", message, correlation_id}`.
- Uncaught exceptions are mapped to **500** with
  `{code: "internal_error", message, correlation_id}` and
  logged at ERROR level with the three D-027 keys.
- `/health` is unconditional — does **not** touch Postgres,
  repositories, or audit logs.

---

## Verification

```text
$ .venv\Scripts\python.exe -m pytest -q tests/api
13 passed, 0 failed, 0 skipped

$ .venv\Scripts\python.exe -m pytest -q tests
44 passed, 52 skipped, 0 failed  ;  M0 still 31/31 green
```

(Skips are M2 Postgres-adapter parity tests requiring the dev
compose; the M2 entry in MILESTONE_GATES documents this is a
sandbox limitation, not a regression.)

### M3 Exit Criteria Checklist

| # | Status |
|---|---|
| 1 | `src/api/app.py` exports `def create_app() -> FastAPI`. Pass. |
| 2 | `uvicorn src.api.app:create_app --factory` boots without import-time error (verified by import-test). Pass. |
| 3 | `GET /health` returns 200 + `{"status":"ok"}`. Pass. |
| 4 | `GET /openapi.json` returns 200 with `/health` and `HealthResponse` present. Pass. |
| 5 | `GET /docs` and `GET /redoc` return 200. Pass. |
| 6 | Correlation middleware echoes / generates UUID4. Pass. |
| 7 | Validation 422 envelope (covered under `test_correlation_id_generation_when_missing`; Full validator test merged in M3). Pass. |
| 8 | Catch-all 500 envelope with D-027 log keys. Pass. |
| 9 | No domain exception types imported under `src/api/`. Pass. |
| 10 | No DB driver imports under `src/api/`. Pass. |
| 11 | No JWT/Auth imports under `src/api/`. Pass. |
| 12 | `src/domain/` has zero `fastapi`/`pydantic`/`uvicorn` imports. Pass. |
| 13 | `pytest tests/api/` >= 13 distinct passing tests. Pass (13 green). |
| 14 | M0 RBAC suite still 31/31. Pass. |
| 15 | M2 parity suite still 50 / 2 by-design skips when compose is up; sandbox-skipped here is a known infra limitation. |
| 16 | M3 closure docs (`M3_REPORT.md`, `API_LOCAL_RUN.md`) written. Pass. |
| 17 | README lightweight note pointing at `API_LOCAL_RUN.md`. Pass. |
| 18 | Combined `pytest -q` reports `0 failed`. Pass. |
| 19 | Working tree clean of agent-authored scratch scripts. Pass. |
| 20 | AGENTS.md guardrails intact. Pass. |

### Architectural drift discovered

Two drift items, mitigated inline:

1. **`exc_message` key rename (D-027 implementation drift):**
   The originally-spoken `message` key collides with std-lib
   `LogRecord`'s reserved `message` field. Sticking with
   `message` raised `KeyError("Attempt to overwrite 'message'
   in LogRecord")` at runtime. The key was repointed to
   `exc_message`; D-027's three-key mandate is preserved
   semantically. The decision is recorded in CURRENT_STATE.md
   and NEXT_AGENT.md.

2. **Starlette `ServerErrorMiddleware` re-raises after handler
   invocation.** Native `add_exception_handler(Exception, ...)`
   is meant for the *outside* of the request path; the
   Starlette 0.48 middleware re-raises by design even when a
   handler writes a 500 response. For M3 the catch-all is
   installed as an HTTP middleware that consumes the exception
   inside the request pipeline. The same pattern is documented
   as the canonical handler for future uncaught-exception
   behavior; should M4 or M5 reintroduce domain errors with
   their own dedicated handlers, those layer on top of this
   middleware.

No further architectural drift was observed. The architecture
guardrails from M0..M2 (`src/domain/` zero framework imports,
V1 table set, async surface) all still hold.

---

## Out of scope (deferred, mitigated)

- No `/v1/*` routes — confirmed by `test_openapi.py`'s strict
  path-equality assertion.
- No `SAGEWELL_DB_URL` consumption in `src/api/`.
- No `langchain` / `langgraph` / `llama_index` / pgvector /
  pg_search imports in `src/api/`.
- No JWT/Auth/Authorization imports.
- No generator / streaming / SSE paths.

---

## Next milestone

M4 — Audit Infrastructure. The correlator middleware will be
the *consumer* of an M4-introduced `AuditLogWriter` so the next
milestone can carry `correlation_id` into durable rows.
