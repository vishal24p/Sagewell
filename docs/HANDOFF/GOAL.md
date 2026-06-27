# V1.x Hardening Goal

Defined by: re-invoking the `define-goal` skill on top of
the V1 release-ready state plus the inspection output at
`docs/HANDOFF/TECHNICAL_ISSUES.md`.

## Quality bar applied

The define-goal quality bar requires the objective to
answer: WHAT concrete thing will be true -- EVIDENCE to
prove it -- QUANTITATIVE bar -- SCOPE bounds -- STOP
condition.

## Objective (single concise string)

> Resolve all 16 issues documented in
> `docs/HANDOFF/TECHNICAL_ISSUES.md` (2 critical, 5 high,
> 5 medium, 4 low) on the `feat/m14-followup` branch,
> while keeping the launch contract `uvicorn
> src.api.app:create_app --factory` DB-free, the M0 RBAC
> suite 100% green (31/31), and the combined M14 release
> gate green (166 + new regression tests >= 167 passed,
> 0 failed, sandbox-skips unchanged).

## Verifier evidence (the four numeric ones)

- `python -m pytest` -- 167+ passed, 0 failed, 52
  skipped, baseline runs in < 6 seconds on developer
  machine.
- `python -m pytest tests/rbac -q` -- 31 passed, 0
  failed.
- `python -m pytest tests/release_gate -q` -- 12 +
  NEW_regression_tests passed.
- `python -m pytest tests/release_gate/test_m14_rbac_suite.py::test_record_guard_verdict_writes_audit_row_via_real_repo -v`
  -- 1 NEW passing test (proves Issues 01 and 02 are
  fixed at the real repository boundary, not just the
  stub repository).

## Specific required behaviors

The next agent must, at minimum, land these:

1. **Issue 01**: extend `src/domain/ports/reason_codes.py`
   `_ALLOWED_REASON_CODES` to include the six M10/M11
   codes (`regex_passed`, `regex_refused_high`,
   `regex_refused_critical`, `llm_guard_allow`,
   `llm_guard_downgrade`, `llm_guard_refuse`).
   Verification: `tests/release_gate` gets a new module
   `test_m14_followup_audit_persistence.py` that runs
   `RecordGuardVerdict.execute(...)` against the real
   `InMemoryAuditLogRepository` for every M10/M11 code
   and asserts no `PersistenceError`.

2. **Issue 02**: `src/api/routers/query.py` must invoke
   `RecordGuardVerdict.execute(...)` after both the M10
   regex-refusal and a future M11 LLM refusal (or after
   the M11 node is added to `run_query.py`). The 400
   envelope payload must be tightened to
   `{code, message, correlation_id}` -- no
   `rule_id=...`. Verification: a new test asserts
   response.json() does NOT contain `rule_id`.

3. **Issue 03**: drop the `1024` branch in
   `src/application/retrieval/retrieve.py:339-348` and
   reference `EMBEDDING_DIM` from
   `src/domain/ports/chunks.py`. The 1024-tolerance
   branch is dead code; removing it.

4. **Issue 04**: widen
   `retrieval_logs.actor_user_id` handling so that
   non-numeric actor ids are persisted as `str` (or
   to a separate `actor_external_subject` column).
   The `actor_id=0`-for-everyone failure mode must not
   redeploy. Update the helper `_resolve_actor_id` or
   remove it. Verification: replace
   `test_unknown_actor_falls_back_to_zero` with a test
   that proves a fixture user `u-m9` ends up in
   `retrieval_logs.actor_user_id` (as `str` or via
   the column rename).

5. **Issue 05**: inject `Clock` into
   `RecordRetrievalLog` + `RecordGuardVerdict`. Replace
   `datetime.utcnow()` with `clock.now(tz=timezone.utc)`.
   Verification: a new test pins the clock and asserts
   the `created_at` is timezone-aware.

6. **Issues 06-11**: dedupe `_clearance_from_str`,
   `actor_to_user_projection`, the correlation-id
   ladder, the M5/M7 audit-write call paths, and rename
   `RecordAuditEvent.__call__` to
   `RecordAuditEvent.execute` for shape consistency. The
   dedupe cannot change behavior; the existing 166 tests
   are the regression.

7. **Issues 12-16**: small test + envelope hygiene.
   Replace inline DTOs with small helpers; rename stub
   fields; tighten the 503 milestone-name hint and the
   400 envelope payload.

## Scope

`src/domain/ports/reason_codes.py`
`src/domain/ports/chunks.py`
`src/application/audit_event/*`
`src/application/observability/{__init__,logs}.py`
`src/application/citations/verify.py`
`src/application/retrieval/retrieve.py`
`src/application/regex_guard/guard.py`
`src/application/llm_guard/guard.py`
`src/application/auth/verify_jwt.py`
`src/application/ingestion/ingest.py` (only where
the audit-write path is changed)
`src/api/routers/query.py`
`src/api/app.py` (DI seam only -- keep the launch
contract DB-free)
`tests/release_gate/*` (add regression tests)
`docs/HANDOFF/TECHNICAL_ISSUES.md` (update with
CLOSED-status for each issue when fixed)

Out of scope:
- V1 schema shifts. The V1 table list is locked.
- M0 access-decision pure function changes. The pure
  function is unchanged at every boundary.
- ARCHITECTURE.md / DATABASE_SCHEMA.md / POLICIES.md /
  WORKFLOWS.md changes. The fix is bounded to the
  application + API surface.
- Capability adoption (Embedding Model, Reranker Model,
  Guardrail Model, Generation Model, RAGAS SDK). D-002
  through D-006 own their own milestones.

## Stop condition

Stop and ask the user when:

- The fix touches `src/domain/access/access_decision.py`
  -- this is the M0 pure function and the changes
  crossing this boundary require an ADR per AGENTS.md.
- The fix touches `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`,
  `POLICIES.md`, or `WORKFLOWS.md` -- these are source-of-
  truth documents and require deliberation.
- The fix introduces an out-of-V1 concept (ACL, multi-
  tenant, OIDC, etc.) -- per AGENTS.md Forbidden Changes.
- Three (3) fix attempts to any single issue fail;
  pause and question the architecture before further
  attempts (per the systematic-debugging skill).
- The M0 RBAC suite (31/31) or the M14 release-gate
  tests regress (any red). Pause and investigate.

## Acceptance signal

Once all 16 issues are CLOSED in TECHNICAL_ISSUES.md
with the corresponding test evidence:

- `git log --oneline feat/m14-followup | head -10`
  shows 1..N commits on the new branch;
- `git ls-remote --heads origin feat/m14-followup`
  shows the new branch pushed;
- `NEXT_AGENT.md` is flipped to point at the
  next-milestone-set discussion (the post-V1 work);
- `PROJECT_STATUS.md` is updated with the V1.x
  hardening row.

## Why this is what it is

Two facts drive the bar:

  1. The audit row for an M10/M11 refusal cannot
     survive today (Issue 01, demonstrated with a
     live `PersistenceError`). The release-gate
     test bar (166 passed) does NOT exercise the
     real `AuditLogRepository` boundary; it uses
     stubs. The closure reports claim
     "release-ready" but the production observability
     for guard rails is broken.

  2. The M10 Regex Guard is wired in the route but
     writes no audit row (Issue 02). The M11 LLM
     Guard is unwired entirely (Issue 02). The
     closure report D-090 says "5 launch-contract
     tests + envelope + M10-refusal + full-stack-
     smoke" -- the M10-refusal test asserts only the
     envelope, NOT the audit row. So the release-
     gate is green while the observability is broken.

Hence: improvements = real, not decorative.
