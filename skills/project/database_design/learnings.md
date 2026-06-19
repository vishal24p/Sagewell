# Database Design Learnings

- V1 has six tables. Anything else needs an ADR.
- The access decision reads from `users` and `documents` only.
- `audit_logs` is the only security event store in V1.
- Incremental re-ingestion keys off `documents.content_checksum`.