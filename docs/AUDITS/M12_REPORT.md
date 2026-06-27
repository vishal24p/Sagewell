# M12 Closure - Audit and Retrieval Logs complete

**Date**: 2026-06-26
**Milestone**: M12 - Audit + Retrieval Logs complete.
**Scope**: Application-side RecordRetrievalLog + RecordGuardVerdict use cases bind the M8/M10/M11 surfaces to the audit_logs / retrieval_logs repository ports. The V1 audit_predicate widens with six M10/M11 reason codes while the strict ReasonCode Literal stays narrowed to the seven M0 codes.
**Status**: CLOSED 2026-06-26 on feat/m12-logs-complete.

---

## Decision IDs Locked

| D-ID | Decision |
|---|---|
| D-086 | M12 ships src/application/observability/logs.py with RecordRetrievalLog + RecordGuardVerdict. Both use cases are framework-free; both delegate to the M2 AuditLogRepository / RetrievalLogRepository Protocol ports. The RecordRetrievalLog use case serializes the typed RetrievalStageStats to the candidate_counts JSON column. The RecordGuardVerdict use case validates the reason_code against ALL_V1_REASON_CODES (a typed predicate over the union of the seven M0 + JWT_INVALID + three M7 ingestion codes + six M10/M11 guard codes) before delegating to the AuditLogRepository. |
| D-087 | ALL_V1_REASON_CODES is the explicit V1 allowed-codes set. The repository-side M2 Pydantic-validated Enum stays narrowed (it accepts only the seven M0 / jwt_invalid / ingestion_succeeded / ingestion_skipped / ingestion_failed codes); the application's predicate widens the application-controlled set with the six M10/M11 codes. New V1 codes extend the predicate, not the repository enum. |

## Files Created

- src/application/observability/__init__.py
- src/application/observability/logs.py
- tests/application/observability/test_logs.py -- 6 tests.

## Verification

Combined pytest 148 passed, 52 skipped, 0 failed (was 142 at M11 closure; net +6 from M12).

## Next milestone

M13 - RAGAS Evaluation (capability port + typed suite shape; SDK adoption deferred per D-006).
