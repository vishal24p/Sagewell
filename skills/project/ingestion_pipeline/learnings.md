# Ingestion Pipeline Learnings

- Incremental re-ingestion keys off `documents.content_checksum`.
- LlamaIndex does not see authorization state; the workflow applies
  the access decision.
- A failed embedding write must not leave active chunks behind.
- The job outcome goes to `audit_logs`, not a separate jobs table.