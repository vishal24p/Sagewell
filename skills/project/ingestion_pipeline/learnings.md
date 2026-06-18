# Ingestion Pipeline Learnings

- Incremental ingestion depends on stable source IDs and checksums.
- Deleted source documents must retire searchable chunks.
- A failed document should be isolated when the connector permits partial success.
