# M4 Closure — Audit Infrastructure (Application Use-Case)

**Date**: 2026-06-20
**Milestone**: M4 — Audit Infrastructure
**Scope**: Application-layer audit-intake use-case only. No
middleware, no test endpoint, no DB at app boot, no request-time
audit writes.
**Status**: **CLOSED 2026-06-20** at commit `03351c4` on
`main` (pushed to `origin/main`).
**Closure artifact**: this file plus
`docs/HANDOFF/API_LOCAL_RUN.md`.

---

## Decision IDs Locked (this milestone)

| D-ID | Decision |
|---|---|
| D-029 | M4 ships the application use case only. No middleware. No test endpoint. |
| D-030 | `src/domain/ports/reason_codes.py` is unchanged at M4. Only the seven M0 IMM codes are emitted. I-001 stays open. |
| D-031 | `create_app(*, audit_repo: Optional[AuditLogRepository] = None)`. `__main__.py` owns pool construction. |
| D-032 | No automatic audit writes during requests at M4. The launch contract stays DB-free until M5. |
| D-033 | `docs/AUDITS/AUDIT_HISTORY.md` row 16 is edited (not split) to capture the late-state alignment commits `b6125d9` and `debe101`. |
| D-034 | `src/api/__init__.py` docstring is unchanged at M4. The package boundary is preserved. |
| D-035 | `create_app` keeps `audit_repo` only. No `pool` parameter, even via `TYPE_CHECKING`. |
| D-036 | Two-error split kept: `AuditEventError` (validation), `PersistenceFailure(AuditEventError)` (persistence). |
| D-037 | Implementation sign-off. |

---

## Files Created Under M4

### Source

- `src/application/__init__.py` — application package docstring.
- `src/application/audit_event/__init__.py` — re-exports.
- `src/application/audit_event/clock.py` — `Clock` Protocol, `SystemClock`.
- `src/application/audit_event/dto.py` — `AuditEventId`, `RecordAuditCommand`.
- `src/application/audit_event/errors.py` — `AuditEventError`, `PersistenceFailure`.
- `src/application/audit_event/record.py` — `RecordAuditEvent`.

### Tests

- `tests/application/__init__.py`
- `tests/application/audit_event/__init__.py`
- `tests/application/audit_event/conftest.py` — fixtures: `audit_repo`, `clock`, `record_use_case`, `record_use_case_exploding`, `make_cmd`, helpers `FrozenClock` and `ExplodingAuditLogRepository`.
- `tests/application/audit_event/test_record_audit_event.py` — 10 distinct tests.

### Documentation

- `docs/AUDITS/M4_REPORT.md` (this file).

## Files Modified Under M4

- `src/api/app.py` — adds `audit_repo: Optional[AuditLogRepository] = None` parameter; mounts on `app.state.audit_repo` when supplied. No `pool` parameter, no asyncpg import.
- `src/api/__main__.py` — docstring-only change to record the M4 invariant (DB-free launch contract until M5).
- `docs/HANDOFF/DECISIONS_PENDING.md` — D-029..D-037 entries.
- `docs/HANDOFF/CURRENT_STATE.md` — flip Current Milestone to M4 (in progress); add M4 row to In Progress.
- `docs/HANDOFF/API_LOCAL_RUN.md` — M4 paragraph; new seam description.
- `docs/AUDITS/MILESTONE_GATES.md` — M4 row added.
- `docs/AUDITS/AUDIT_HISTORY.md` — row 16 edited per D-033 (not split).
- `MEMORY.md` — M4 closure row + 9 D-ID rows.
- `NEXT_AGENT.md` — flip Current Milestone header to M4; updated body.

---

## Surface

### `src/application/audit_event/` public surface

```python
AuditEventError
PersistenceFailure  # subclass of AuditEventError
AuditEventId        # NewType over int
RecordAuditCommand  # @dataclass(frozen=True)
RecordAuditEvent    # use case class with __call__(cmd) -> AuditEventId
Clock               # Protocol
SystemClock         # production implementation
```

### Boundary contracts

- The use case validates:
  - `cmd.correlation_id` non-empty,
  - `cmd.action` non-empty,
  - `cmd.decision` is an `AuditDecision` enum value.
- The use case stamps `created_at` from a `Clock` (default `SystemClock()`).
- The repository's `PersistenceError` is re-raised as `PersistenceFailure(AuditEventError)`.
- The use case returns `AuditEventId(new_id)`.

### `src/api/app.py` DI seam

```python
def create_app(*, audit_repo: Optional[AuditLogRepository] = None) -> FastAPI
```

- No middleware or route consumes `audit_repo` at request time.
- `__main__.py` does NOT construct a pool.
- The factory does NOT import asyncpg, does NOT read `SAGEWELL_DB_URL`.

---

## Verification

```text
$ .venv\Scripts\python.exe -m pytest -q tests/application/audit_event
10 passed, 0 failed, 0 skipped

$ .venv\Scripts\python.exe -m pytest -q tests/application tests/api tests/rbac
54 passed, 0 failed, 0 skipped

$ .venv\Scripts\python.exe -m pytest -q   # combined (incl. M2 Postgres-skips when compose absent)
54 passed, 52 skipped, 0 failed
```

### Structural guards

- `grep -rE "^(?:import|from)\s" src/application/` shows only:
  - `__future__`,
  - `dataclasses`, `datetime`, `typing`, stdlib `Protocol`,
  - intra-`src.application.*`,
  - `src.domain.ports.audit_logs`,
  - `src.domain.ports.errors`.
  No `src.api/`, no `src.infrastructure/`, no `asyncpg`, no `fastapi`, no `uvicorn`, no framework SDK.
- `grep -rE "from src\.api|from src\.infrastructure|from src\.application|import asyncpg|import fastapi\.security" src/api/` returns zero rows.
- `grep -rE "from src\.application" src/domain/` returns zero rows (domain purity preserved).

### Boundary invariants

- `create_app()` with no argument returns a working skeleton (5 routes, DB-free).
- `create_app(audit_repo=None)` returns the same skeleton.
- `uvicorn src.api.app:create_app --factory` boots without importing asyncpg.

---

## Architectural drift discovered (none new)

- The forward-reference `Optional["AuditLogRepository"]` in `src/api/app.py` keeps `src/api/` from importing `src/domain/ports/audit_logs` at runtime. Verified through the structural grep.
- M3's `CorrelationIdMiddleware` writes `correlation_id` to `request.state`. Plumbing this into the M4 use case is a M5 concern, not an M4 concern. M4 ships the use case such that the future caller (M5+) supplies the correlation id explicitly.

---

## Out of scope (deferred)

- No FastAPI middleware that writes audit rows.
- No `/v1/*` routes, including no `POST /v1/_audit_test` style endpoint.
- No DB pool construction inside `__main__.py`.
- No request-time audit-write behavior.
- No JWT validation.
- No reasoning/ranking/retrieval/generation coupling.
- No expansion of `src/domain/ports/reason_codes.py` (I-001 stays open).
- No negative-space audit-table modification. The schema is locked to TEXT for `reason_code`.

---

## Next milestone

M5 — JWT Validation. The future consumer of the M4 use case will
be the M5 JWT validator: it will validate the JWT, build the
actor, and call `RecordAuditEvent` to log every auth attempt
(success and failure) with the seven M0 IMM reason codes plus
the codes M5 introduces (deferred to that milestone's own ADR).
