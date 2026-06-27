# M10 Closure - Regex Guard

**Date**: 2026-06-26
**Milestone**: M10 - Regex Guard.
**Scope**: Pattern-based refusals on the /v1/query primary request path per POLICIES.md ordering (JWT -> Regex Guard -> RBAC Authorization -> Retrieval -> LLM Guard -> Generation).
**Status**: CLOSED 2026-06-26 on feat/m10-regex-guard.

---

## Decision IDs Locked (this milestone)

| D-ID | Decision |
|---|---|
| D-081 | M10 introduces src/domain/ports/regex_guard.py with the typed Rule (rule_id, tier, compiled pattern, description), RegexRuleCatalog (versioned, duplicate-id-rejecting), RegexGuardVerdict ({allowed, rule_id, tier, description}), RegexTier (HIGH / CRITICAL), and the default V1 catalog. |
| D-082 | M10 ships src/application/regex_guard/guard.py with the RegexGuard use case. Pure; carries the versioned catalog. Reason codes: regex_passed, regex_refused_high, regex_refused_critical. Blank-query cascades to a sentinel blank_query rule. CRITICAL tier rules are evaluated first so a critical-tier match wins over a high-tier one. |
| D-083 | The M10 guard integrates via the create_app(... regex_guard=Optional[RegexGuard]) DI seam. Without wiring the route runs the M9 pipeline directly (preserving the M9 launch contract); a refusal returns a 400 envelope with code=regex_refused, message carrying rule_id + tier + reason_code. |

## Files Created Under M10

### Source

- src/domain/ports/regex_guard.py -- Rule, RegexRuleCatalog, RegexGuardVerdict, RegexTier, default_v1_catalog.
- src/application/regex_guard/__init__.py -- package surface.
- src/application/regex_guard/guard.py -- RegexGuard use case + command / result dataclasses.

### Tests

- tests/application/regex_guard/test_regex_guard.py -- six tests (happy pass, high-tier match, critical-tier match, document-authority claim, blank query, catalog-version round-trip).
- tests/api/test_v1_query_route.py -- gained a regex_refused 400 envelope assertion.

## Verification

Combined pytest 137 passed, 52 skipped, 0 failed (was 130 at M9 closure; net +7 from M10).

## Architectural decisions (review)

- The Regex Guard precedes the M9 retrieval + citation-verification pipeline. It is pure; it never writes audit rows; the workflow boundary records the reason_code through M12 RecordGuardVerdict.
- The pattern set is versioned (V1 catalog); future M10-extension milestones can swap catalogs without touching the application surface.
- The launch contract remains DB-free: the route runs the M9 pipeline directly when no guard is wired.

## Next milestone

M11 - LLM Guard. Context-aware prompt-protection step that runs AFTER retrieval and BEFORE generation.
