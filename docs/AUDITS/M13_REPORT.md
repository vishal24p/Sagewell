# M13 Closure - RAGAS Evaluation

**Date**: 2026-06-26
**Milestone**: M13 - RAGAS Evaluation (capability port + typed suite shape).
**Scope**: M13 ships the typed RAGAS case shape, the four V1 metrics + RAGAS verdict + capability-shaped scorer port. The RAGAS SDK is intentionally NOT pinned; open question D-006 owns the SDK adoption milestone.
**Status**: CLOSED 2026-06-26 on feat/m13-ragas.

---

## Decision IDs Locked

| D-ID | Decision |
|---|---|
| D-088 | M13 introduces src/domain/ports/ragas.py with the typed RagasMetric enum (Faithfulness, Context Precision, Context Recall, Answer Relevancy), RagasCase (case_key, query, answer, retrieved_contexts, ground_truth_contexts, ground_truth_answer, minimums), RagasScore (per-metric 0..1 floats + rationale), RagasScorerPort (capability-shaped), RagasVerdict (passed / failure_reason). |
| D-089 | M13 ships src/application/evaluation/ragas.py with the RunRagasCase use case. Async; invokes the configured scorer port with a typed RagasCase and returns a typed RagasVerdict. Threshold rule: every metric in case.minimums (when set) must be at or above its threshold; metrics absent from minimums are informational. Failure reasons summarize breaches with the typed metric name. |

## Files Created

- src/domain/ports/ragas.py
- src/application/evaluation/__init__.py
- src/application/evaluation/ragas.py
- tests/application/evaluation/test_ragas.py -- 6 tests.

## Verification

Combined pytest 154 passed, 52 skipped, 0 failed (was 148 at M12 closure; net +6 from M13).

## Next milestone

M14 - End-to-end Hardening.
