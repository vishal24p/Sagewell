# M5 Closure — JWT Validation

**Date**: 2026-06-21
**Milestone**: M5 — JWT Validation
**Scope**: HS256-only JWT verification on every non-public request. Typed `AuthActor` projection. Audit row on every failure via the M4 `RecordAuditEvent`. Auth middleware at the API boundary. **No** JWKS, **no** RS256, **no** multi-issuer resolver.
**Status**: **CLOSED 2026-06-21** at this commit on `rag-langgraph`.

---

## Decision IDs Locked (this milestone)

| D-ID | Decision |
|---|---|
| D-001 | HS256 only at M5. Shared secret from `SAGEWELL_JWT_SECRET`. Reintroducing RS256 / JWKS is a future ADR. |
| D-038 | M5 ships a dedicated `src/application/auth/` package as a sibling to `src/application/audit_event/`. Imports only from `src/domain/ports/` and intra-application. |
| D-039 | M5 introduces a `src/api/middleware/auth.py` middleware that runs `VerifyJwtToken` on every request. The skip set is `{"/health", "/docs", "/redoc"}` only; `/openapi.json` is JWT-protected. |
| D-040 | Q1: trust the JWT after successful verification; no DB lookup in the auth path. Q2: failure-path audit rows use an `unknown-user` actor carrier. Q3: `/openapi.json` requires auth; only `/health`, `/docs`, `/redoc` skip. |
| D-041 (this milestone) | Cross-layer: `pytest_asyncio` autouse mode resolves the `VerifyJwtToken` async call inside the middleware via the standard FastAPI ASGI middleware contract. `verify_jwt` is resolved at request time through `scope["app"].state.verify_jwt` (not at module load); this keeps the middleware a stateless glue layer. |
| D-042 (this milestone) | Cross-layer: `src/api/middleware/auth.py` is a pure-ASGI middleware (no `BaseHTTPMiddleware`) so 401 envelopes are written without triggering Starlette's `ServerErrorMiddleware` re-raise pattern that the M3 catch-all had to work around (F-30). |
| D-043 (this milestone) | Auth-package import-graph invariants: `src/application/auth/**` does not import `fastapi`, `pydantic`, `uvicorn`, `asyncpg`, `psycopg`, `sqlalchemy`, or any framework SDK. Verified by `python -c "import ast; ..."` static analysis; see `## Verification` below. |
| D-044 (this milestone) | Reason-code widening at M5: `src/domain/ports/reason_codes.py` adds `JWT_INVALID = "jwt_invalid"` to the application's allow-list (`is_allowed_reason_code`). The `ReasonCode` literal at the bottom **stays narrowed** to the seven M0 access-decision codes so the literal continues to bound the access-decision's output shape. New V1 codes widen the predicate, not the literal. |

---

## Files Created Under M5

### Source

- `src/application/__init__.py` — populated by M4; unchanged.
- `src/application/auth/__init__.py` — package surface.
- `src/application/auth/dto.py` — `VerifyJwtTokenCommand`, `AuthActor`, `UNKNOWN_USER_ACTOR`, unknown-user carrier constants.
- `src/application/auth/errors.py` — typed-failure hierarchy: `AuthFailure`, `JwtMissing`, `JwtMalformed`, `JwtBadSignature`, `JwtExpired`, `JwtInvalid`.
- `src/application/auth/signer.py` — `JwtSigner` Protocol, `JwtClaims` NamedTuple, `HS256JwtSigner`.
- `src/application/auth/verify_jwt.py` — `VerifyJwtToken` use case (the canonical entry point).
- `src/api/middleware/auth.py` — `JwtAuthMiddleware`, `PUBLIC_PATHS`, `_extract_header` helper.

### Tests

- `tests/application/__init__.py` — populated by M4; unchanged.
- `tests/application/auth/__init__.py`
- `tests/application/auth/conftest.py`
- `tests/application/auth/test_hs256_signer.py` — 5 distinct tests.
- `tests/application/auth/test_verify_jwt.py` — 5 distinct tests.
- `tests/api/test_auth_middleware.py` — 6 distinct tests covering happy path, skip set, audit-row metadata on missing / bad-signature / success paths.

### Documentation

- `docs/AUDITS/M5_REPORT.md` (this file).
- `docs/AUDITS/FINDINGS.md` — entries F-31..F-34.
- `MEMORY.md` — M5 closure row.
- `docs/AUDITS/AUDIT_HISTORY.md` — row 18 added.
- `docs/AUDITS/MILESTONE_GATES.md` — M5 row marked **Closed**.
- `docs/HANDOFF/CURRENT_STATE.md` — M5 row added to Completed.
- `docs/HANDOFF/DECISIONS_PENDING.md` — D-001 carve-out, D-038, D-039, D-040 added to Approved; D-041..D-044 captured.
- `NEXT_AGENT.md` — Current Milestone flips to M6 (LangGraph Skeleton) — actor-aware.

---

## Files Modified Under M5

- `pyproject.toml` — adds `pyjwt>=2.8,<3.0` (runtime dep used by `HS256JwtSigner`).
- `src/api/app.py` — `create_app` accepts an optional `jwt_signer` keyword. When supplied, an `app.state.verify_jwt` `VerifyJwtToken` is constructed and the auth middleware mounts. The auth middleware sits between the correlation middleware and the application stack (`CorrelationIdMiddleware` is the outer layer).
- `src/api/__main__.py` — `__main__` reads `Settings.jwt_secret` and constructs an `HS256JwtSigner(secret=...)` when set, passing it through to `create_app`. The launch contract stays DB-free when `SAGEWELL_DB_URL` is unset.
- `src/api/settings.py` — adds `jwt_secret: Optional[bytes]` to `Settings`. No default; the auth middleware is no-op when unset.
- `src/domain/ports/reason_codes.py` — widens the application-level allow-list to add `jwt_invalid`. The `ReasonCode` Literal is intentionally **not** widened (so the literal still bounds the access-decision output shape; widening lives in `is_allowed_reason_code`).
- `tests/api/conftest.py` — adds `jwt_signer`, `frozen_now`, `in_memory_audit_repo`, `authed_app`, `authed_client` fixtures.
- `tests/application/audit_event/test_record_audit_event.py` — adds an explicit `reason_code="jwt_invalid"` smoke test against the existing `record_use_case` to confirm the M4 use case still accepts the new code through its existing code-path.
- `docs/HANDOFF/API_LOCAL_RUN.md` — adds an M5 paragraph describing the `SAGEWELL_JWT_SECRET` env switch and the dev launch.

(M4's `create_app(audit_repo=None)` invariant — no `audit_repo` parameter leakage outside the factory — is preserved; the only M5 additive parameter is `jwt_signer`.)

---

## Surface

### Public use-case + signer interface (`src/application/auth/`)

```python
# Errors
AuthFailure
JwtMissing       # code = "jwt_missing"
JwtMalformed     # code = "jwt_malformed"
JwtBadSignature  # code = "jwt_bad_signature"
JwtExpired       # code = "jwt_expired"
JwtInvalid       # code = "jwt_invalid"

# DTOs
VerifyJwtTokenCommand     # @dataclass(frozen=True) {token, correlation_id}
AuthActor                 # @dataclass(frozen=True)
                          #   {user_id, department, clearance,
                          #    role, correlation_id}
UNKNOWN_USER_ACTOR        # typed failure-carrier constant
UNKNOWN_USER_CARRIER_METADATA_TAG = "auth_failure_carrier"
UNKNOWN_USER_CARRIER_METADATA_VALUE = "unknown-user"

# Signer
JwtSigner                 # Protocol
JwtClaims                 # NamedTuple(user_id, department, clearance, role)
HS256JwtSigner(secret: bytes, leeway_seconds: int = 5)

# Use case
VerifyJwtToken(signer, audit_repo=None, clock=None)
                          # async __call__(cmd) -> AuthActor
```

### Boundary contracts

- `VerifyJwtToken` is async. `await use_case(cmd)` either returns the typed `AuthActor` (success) or raises an `AuthFailure` subclass (failure).
- The use case validates `cmd.token` upstream. An empty token raises `AuthFailure` synchronously, **after** writing the failure row through M4's `RecordAuditEvent`.
- The use case re-raises the signer's typed `AuthFailure` subclass unchanged when verification fails.
- The audit row format on failure is the M4 contract: `actor_user_id=None`, `action="auth.jwt.evaluated"`, `decision=AuditDecision.FAILED`, `reason_code="jwt_invalid"`, `correlation_id=cmd.correlation_id`, `metadata={"auth_failure_carrier": "unknown-user", "auth_failure_code": "..."}`.

### `src/api/middleware/auth.py`

- Pure-ASGI middleware, mirroring `CorrelationIdMiddleware`.
- Resolves `verify_jwt` from `scope["app"].state.verify_jwt` at request time. No-op when `app.state.verify_jwt` is not set (the M3 launch contract).
- Skip set: `{"/health", "/docs", "/redoc"}` (exposed as `PUBLIC_PATHS`).
- Missing / malformed `Authorization` headers also flow through `VerifyJwtToken` (empty token) so every failure produces an audit row.
- On any `AuthFailure`, returns the canonical 401 envelope `{code: "auth_failed", message, correlation_id}`.
- Successful verification attaches the typed `AuthActor` to `scope["state"]["actor"]` for M6+ consumers.

### `create_app` DI seam

```python
def create_app(
    *,
    audit_repo: Optional[AuditLogRepository] = None,
    jwt_signer: Optional[JwtSigner] = None,
) -> FastAPI
```

When `jwt_signer` is supplied:
1. `VerifyJwtToken(signer=jwt_signer, audit_repo=audit_repo, clock=SystemClock())` is bound to `app.state.verify_jwt`.
2. The middleware mounts on every request that is not in `PUBLIC_PATHS`.

When `jwt_signer is None`:
1. `app.state.verify_jwt` is unset.
2. The middleware mounts but is a no-op (every path passes through; the M3 launch contract is preserved).

---

## Verification

```text
$ .venv\Scripts\python.exe -m pytest -q tests/api
19 passed, 0 failed, 0 skipped

$ .venv\Scripts\python.exe -m pytest -q tests/application/auth
10 passed, 0 failed, 0 skipped

$ .venv\Scripts\python.exe -m pytest -q tests/api tests/application tests/rbac
73 passed, 0 failed, 0 skipped

$ .venv\Scripts\python.exe -m pytest -q   # combined (incl. M2 Postgres-skips when compose absent)
73 passed, 52 skipped, 0 failed
```

### Structural guards (the M5 prelude spec from `NEXT_AGENT.md`)

- `grep -rE "fastapi|pydantic|uvicorn" src/domain/` — zero rows. Domain purity preserved.
- `grep -rE "asyncpg|psycopg|sqlalchemy" src/application/` — zero rows (all matches are docstring-only `no asyncpg` decls, not import statements).
- AST-based import-statement scan (Python script) returns zero hits for any of the bad-import set in `src/application/**` and `src/domain/**`.

### Reason-code allow-list widening (M5 layer)

- `is_allowed_reason_code("jwt_invalid")` returns `True`.
- The seven M0 codes still pass.
- Any other string fails closed (existing F-29/F-30 invariant from M2 carries forward).
- `AuditLogRepository.append()` (in-memory + Postgres) is the validation point.

### Auth middleware contract

- `/health`, `/docs`, `/redoc` skip the middleware: 200 even when `jwt_signer` is wired.
- `/openapi.json` returns 401 when `jwt_signer` is wired and `Authorization` is missing.
- Same `/openapi.json` returns 200 when `create_app()` is called with no `jwt_signer` (M3 default).
- A non-skip path (registered by the test ephemerally at `/protected`) returns 200 with a valid HS256 token and 401 with missing / bad-signature tokens.
- A missing-Authorization request produces exactly one M4 audit row with `reason_code="jwt_invalid"` and metadata `{"auth_failure_carrier": "unknown-user", "auth_failure_code": "jwt_missing"}`.
- A bad-signature request produces exactly one M4 audit row with `reason_code="jwt_invalid"` and metadata with `auth_failure_code="jwt_bad_signature"`.
- A success path produces zero audit rows and succeeds with 200.

### Local-run contract

- `SAGEWELL_JWT_SECRET` unset: `create_app()` boots DB-free; `/health`, `/openapi.json`, `/docs`, `/redoc` all return 200.
- `SAGEWELL_JWT_SECRET` set: `create_app(jwt_signer=HS256JwtSigner(secret=...))` boots; `/health` and the dev UI still return 200; `/openapi.json` requires a valid HS256 token.

---

## Architectural drift discovered (none new)

- The M5 middleware sits between the correlation middleware and the application stack. This is intentional: the auth middleware must carry the request's `correlation_id` on the 401 envelope, and `CorrelationIdMiddleware` writes `scope["state"]["correlation_id"]` outer-most.
- The audit-row best-effort failure handling in `VerifyJwtToken` keeps the canonical 401 envelope behavior even when the underlying audit write `PersistenceFailure`s. Audit-write failures are logged at WARNING with the D-027 log keys (`correlation_id`, `exception_type`, `exc_message`) and never surface to the caller; the auth failure is the canonical user-visible error.
- The `JwtSigner.verify()` method disables PyJWT's built-in `exp` validation (`verify_exp = False`) and re-implements `exp` math against the use case's `Clock.now()`. This keeps the verification boundary testable against a frozen clock and avoids `clock skew` race from the local wall clock. PyJWT still validates the signature against the configured secret.
- `tests/application/auth/test_hs256_signer.py` uses pyjwt directly to mint tokens that omit a required claim. This requires the test secret to match the fixture secret exactly; the production path uses `HS256JwtSigner.sign(claims=...)` and never afford an `actor_user_id`-derived secret mismatch.

---

## Findings raised during M5

| ID | Tag | Title | Status |
|---|---|---|---|
| F-31 | MEDIUM | `JwtAuthMiddleware._dispatch_token` and `_dispatch_failure` referenced a bare `verify_jwt` name that Python does not resolve from the enclosing `__call__` method scope. Caused 500 responses on every non-skip path during initial verification. Fix: pass `verify_jwt` as an explicit keyword argument from `__call__` into the dispatcher methods. | RESOLVED this milestone |
| F-32 | LOW | The ephemeral `/protected` route in `tests/api/test_auth_middleware.py` declared `async def _echo_actor(request)` without a `Request` type annotation, causing FastAPI to interpret `request` as a query parameter (HTTP 422 instead of 200). Fix: add `request: Request`. | RESOLVED this milestone |
| F-33 | LOW | Several test HS256 secrets were below PyJWT's recommended 32-byte minimum (RFC 7518 3.2). `InsecureKeyLengthWarning` was emitted at every `encode`/`decode`. Fix: bump `_SEED_SECRET` and `alt_hs256_signer` to 32+ bytes; trace through the `test_hs256_signer.py` literal that bypasses the fixture. | RESOLVED this milestone |
| F-34 | LOW | The `app.state.verify_jwt` runtime resolution in the middleware uses `scope["app"].state`. The middleware class itself stores reference to its parent (inner wrapped app) rather than the FastAPI host application. Starlette injects the FastAPI instance via `scope["app"]`; the runtime lookup must read `scope.get("app")`, not `self._app`, to resolve auth state correctly. Fix: use `scope.get("app")` and `getattr(fastapi_app.state, "verify_jwt", None)`. | RESOLVED this milestone |

---

## Out of scope (deferred)

- No JWKS endpoint, no fetch of issuer public keys. M5 is HS256-only.
- No `/v1/*` routes that proxy to retrieval or generation. M5 ships the auth gate; M6 adds the LangGraph skeleton.
- No RBAC / retrieval / generation coupling in the auth middleware. The middleware is a thin glue layer.
- No expansion of the access-decision `ReasonCode` Literal. The widening of `is_allowed_reason_code` is **application-side only**; the access-decision's output type still returns the seven M0 codes.
- No automatic audit-row writes on successful authentication. The M5 audit path is failure-only; success rows are deferred to M12.
- No DB-construction inside `__main__.py` when `SAGEWELL_DB_URL` is unset. The launch contract stays DB-free.
- No negative-space audit-table modification; `audit_logs.reason_code` stays TEXT with no DB-level constraint.

---

## Next milestone

M6 — LangGraph Skeleton (actor-aware). The future consumer of
M5's `verify_jwt` is the M6 workflow entry point. The
`AuthActor` carried on `request.state.actor` is the canonical
input to the typed LangGraph state
`{user_id, department, clearance, role, correlation_id}`.
