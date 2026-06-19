# Architecture Review Learnings

- The access decision is a single pure function: department match (or
  ALL) AND clearance greater-than-or-equal.
- The access decision runs at three boundaries, not one.
- Retrieval is dense + BM25 + RRF + cross-encoder; no shortcuts.
- Prompt protection is part of the primary request path.
- Models are capability-based in V1; do not pin identifiers.