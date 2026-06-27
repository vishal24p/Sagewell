# M11 Closure - LLM Guard

**Date**: 2026-06-26
**Milestone**: M11 - LLM Guard (capability-shaped).
**Scope**: Context-aware prompt-protection orchestrator + capability-shaped Guardrail Model port. Open question D-004 owns the hosted-Guardrail Model adoption milestone.
**Status**: CLOSED 2026-06-26 on feat/m11-llm-guard.

---

## Decision IDs Locked

| D-ID | Decision |
|---|---|
| D-084 | M11 introduces src/domain/ports/llm_guard.py with the typed GuardrailVerdict (classification ALLOW/DOWNGRADE/REFUSE, rationale, dropped_chunk_ids), GuardrailModelPort (capability-shaped), LLMGuardCommand / LLMGuardResult dataclasses, and reason codes llm_guard_allow, llm_guard_downgrade, llm_guard_refuse. |
| D-085 | M11 ships src/application/llm_guard/guard.py with the LLMGuard use case. Async; invokes the configured model port with a typed GuardrailInput; returns the typed result. Typed errors: LLMGuardEmptyInputError, LLMGuardUnavailableError, LLMGuardError (base). The use case never writes audit rows; the workflow boundary records through M12 RecordGuardVerdict. |

## Files Created

- src/domain/ports/llm_guard.py
- src/application/llm_guard/__init__.py
- src/application/llm_guard/guard.py
- tests/application/llm_guard/test_llm_guard.py -- 5 tests.

## Verification

Combined pytest 142 passed, 52 skipped, 0 failed (was 137 at M10 closure; net +5 from M11).

## Next milestone

M12 - Audit and Retrieval Logs complete.
