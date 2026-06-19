# Retrieval Engine Learnings

- V1 retrieval is dense + BM25 + RRF + cross-encoder. No shortcuts.
- The access decision runs before retrieval and after reranking.
- LlamaIndex provides retrieval abstractions; authorization is not
  its concern.
- Retrieval configuration is recorded for every retrieval_logs row.