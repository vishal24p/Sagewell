"""M8 retrieval application package.

The `RetrieveAuthorizedCandidates` use case is the application-side
orchestrator that wires:

  - The M0 access-decision pure function (`src/domain/access/`).
  - The M7 typed-state + M8 typed-query + M8 typed-result projections
    (`src/domain/ports/retrieval.py`).
  - The M7 `QueryEmbedderProtocol` (re-exported from
    `src/domain/ports/retrieval.py`; uses the M7 embedding capability).
  - The M8 framework-free protocol adapters:
    `DenseRetrieverProtocol`, `Bm25RetrieverProtocol`, `RerankerProtocol`.

Pipeline (mirrors `ARCHITECTURE.md` retrieval architecture and the
V1 query-and-answer workflow steps 5..10):

  1. Pre-retrieval: compute the access-decision policy filter
     (`AccessPolicyFilter`) from the typed actor + the canonical
     (department + clearance + ALL) tuple.
  2. Embed the normalized query through the capability-based
     embeddings; produce a single dense vector.
  3. Dense retrieval against pgvector with the projected
     `AccessPolicyFilter` translated into a SQL `WHERE` clause.
  4. BM25 retrieval against pg_search with the same projection.
  5. RRF fusion across dense + BM25 ranked lists (pure function).
  6. Cross-encoder reranking on the fused list (capability-based).
  7. Post-rerank decision: re-apply the access decision on every
     survivor; drop candidates whose documents evaluate deny.
  8. Persist `RetrievalStageStats` through the future retrieval_logs
     port (M12 completes this; M8 emits the typed stats).

The use case ships type-safe and framework-free. The framework
adapters live under `src/infrastructure/retrieval/` and bind the
typed ports to pgvector / pg_search / LlamaIndex / Reranker SDKs.
"""
from __future__ import annotations

import logging

from src.application.retrieval.errors import (
    AccessDecisionUnavailableError,
    EmptyRetrievalError,
)
from src.application.retrieval.retrieve import (
    RetrieveAuthorizedCandidates,
    RetrieveAuthorizedCommand,
    AuthorizationOutcome,
)

_log = logging.getLogger(__name__)


__all__ = [
    "RetrieveAuthorizedCandidates",
    "RetrieveAuthorizedCommand",
    "AuthorizationOutcome",
    "AccessDecisionUnavailableError",
    "EmptyRetrievalError",
]
