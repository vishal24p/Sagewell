"""V1 retrieval ports (M8).

The four mandatory retrieval stages (per `skills/project/retrieval_engine/`):

  - Dense Retrieval.
  - BM25 Retrieval.
  - RRF Fusion.
  - Cross-Encoder Reranking.

`DocumentChunkerProtocol` and `EmbeddingModelProtocol` are part of
the M7 ingestion surface and live in `src/domain/ports/ingestion.py`.
The M8 ports below are framework-free protocols that the four
retrieval adapters (live under `src/infrastructure/retrieval/`)
implement.

V1 access-decision integration at the M8 boundaries:

  - Pre-retrieval SQL filter: the access decision lowers the
    `(user.department, document.department) +
    (user.clearance, document.required_clearance)` pair into a
    typed `AccessPolicyFilter` projection that the dense / BM25
    adapters translate into a SQL `WHERE` clause. The decision
    is computed by the M0 pure function; this module only carries
    the projection shape so the adapters cannot accidentally
    re-implement the rule.
  - Post-rerank drop: after the cross-encoder rerank, the
    orchestrator applies the access decision again on the
    candidate list. Every chunk whose document fails the
    decision is dropped.

Boundary contract:

  - All retrieval ports are async. The framework adapters may
    wrap a sync pgvector/pg_search call behind await.
  - Frameworks (pgvector, pg_search, LlamaIndex retriever
    abstractions, LangGraph node wrappers) live under
    `src/infrastructure/`. The application package
    (`src/application/retrieval/`) imports the protocols only.
  - `QueryEmbedderProtocol` mirrors M7's embedding model and
    lives at the M7 ingestion port; the dense retrievers call
    it directly. M8 does NOT introduce a second embedding
    surface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Protocol, Sequence

from .chunks import EMBEDDING_DIM


@dataclass(frozen=True)
class AccessPolicyFilter:
    """Projection of the M0 access decision for SQL filter use.

    The dense / BM25 adapters translate this projection into a
    SQL `WHERE` clause. The pure-function decision is preserved
    end-to-end: the projection is computed once by the M0
    function; the adapters do not re-implement the rule.

    - `allowed_departments`: iterable of `Document.department`
      values the actor's `user.department` may match. When
      empty, no department restriction is applied (the actor's
      department is missing and the decision deny-trumps).
    - `minimum_clearance`: the actor's `user.clearance`.
      Documents at or below this clearance are eligible.
    - `decision_outcome`: the literal `(allowed, reason)` pair
      from the M0 decision function. Adapters must NOT alter
      the decision; the projection is sealed by the M0
      function caller.
    """
    allowed_departments: tuple[str, ...]
    minimum_clearance: str  # Clearance value
    decision_outcome: tuple[bool, str]


@dataclass(frozen=True)
class RetrievalQuery:
    """The query the orchestrator submits to every retriever.

    - `query_text`: the (already-normalized, regex-guard-passed)
      user-supplied question. The retriever does NOT do its own
      normalization; regex-guard work happens upstream at M10.
    - `top_k`: the per-stage retriever cap. The adapters return
      at most `top_k` candidates.
    - `access_filter`: the projection from above. RRF drops
      candidates whose documents evaluate `False` against this
      filter; the dense / BM25 SQL `WHERE` clauses additionally
      restrict the underlying query.
    - `correlation_id`: the per-request trace that the future
      `retrieval_logs` rows will carry.
    """
    query_text: str
    top_k: int
    access_filter: AccessPolicyFilter
    correlation_id: str


@dataclass(frozen=True)
class RetrievalCandidate:
    """A single candidate that emerges from Dense or BM25.

    - `chunk_id` / `document_id`: the canonical row ids.
    - `dense_score`: vector cosine similarity (Dense only).
      `None` for BM25 candidates.
    - `bm25_score`: BM25 score (BM25 only). `None` for Dense
      candidates.
    - `ordinal`: the chunk's position within the document.
    - `text_preview`: the first ~120 characters of the chunk
      text, useful for observability rows but never persisted
      verbatim.
    - `document_projection`: optional `DocumentProjection`
      carried by adapters that have already projected the
      document's authorization columns (the M8 in-memory
      adapter and the future pgvector/pg_search adapters).
      The post-rerank drop reads this field; when it is
      `None`, the drop is deferred to the M9
      citation-verification step (per `WORKFLOWS.md`).
    """
    chunk_id: int
    document_id: int
    ordinal: int
    dense_score: Optional[float] = None
    bm25_score: Optional[float] = None
    text_preview: Optional[str] = None
    document_projection: Optional["DocumentProjection"] = None


@dataclass(frozen=True)
class RankedCandidate:
    """A fused-or-reranked candidate.

    `stage` tags where the score originated: `dense`, `bm25`,
    `fused` (RRF result), `reranked` (cross-encoder output).
    The score is on the project's canonical scale per stage:
      - dense: cosine similarity in `[-1, 1]`.
      - bm25: ParadeDB `score` value (distribution-specific).
      - fused: RRF reciprocal rank, in `[0, 1]`.
      - reranked: cross-encoder output, monotone but
        distribution-specific.
    """
    candidate: RetrievalCandidate
    score: float
    stage: str  # "dense" | "bm25" | "fused" | "reranked"


@dataclass(frozen=True)
class RetrievalStageStats:
    """Per-stage counts emitted to the future retrieval_logs row.

    - `dense_count`: candidates returned by the dense retriever.
    - `bm25_count`: candidates returned by the BM25 retriever.
    - `fused_count`: candidates returned by RRF fusion.
    - `rerank_count`: candidates returned by the cross-encoder
      reranker.
    - `after_access_count`: candidates that survive the
      post-rerank access decision drop.
    """
    dense_count: int
    bm25_count: int
    fused_count: int
    rerank_count: int
    after_access_count: int


class QueryEmbedderProtocol(Protocol):
    """Embedder re-exported from the M7 ingestion boundaries.

    M8's dense retriever queries the same capability-shaped
    embedder that ingestion uses; M7 lives at this seam
    because the same capability is reused (re-embedding at
    query time lands here too). Re-exported at
    `src/domain/ports/retrieval.py` so a future refactor may
    split ingestion / query-time embeddings without altering
    the application package's surface.

    Implementations:

      - `src/infrastructure/ingestion/embedding.py.DeterministicHashEmbeddingModel`
        (M7 stub; capability-deferred).
      - The M8 future production embedder lands at the
        capability-adoption milestone (open question D-002).
    """

    def embed(self, text: str) -> list[float]: ...


class DenseRetrieverProtocol(Protocol):
    """Dense retrieval (pgvector cosine) at the M8 boundary.

    The implementation translates the `AccessPolicyFilter`
    into the SQL `WHERE` clause that pre-filters by
    `documents.department`, `chunks.status='active'`, and
    `documents.required_clearance`. The application package
    imports the protocol only.
    """

    async def retrieve(
        self,
        query: RetrievalQuery,
        embedding: list[float],
    ) -> Sequence[RetrievalCandidate]: ...


class Bm25RetrieverProtocol(Protocol):
    """BM25 retrieval (pg_search) at the M8 boundary.

    The implementation translates the `AccessPolicyFilter`
    into the `BM25` query's pre-filter, matching the dense
    filter on `documents.department` /
    `documents.required_clearance` to keep the candidate
    sets aligned.
    """

    async def retrieve(
        self,
        query: RetrievalQuery,
    ) -> Sequence[RetrievalCandidate]: ...


class RerankerProtocol(Protocol):
    """Cross-encoder reranker at the M8 boundary.

    Capability-based per `Reranker Model`. The implementation
    is the future milestone that adopts the Reranker
    capability (open question D-003); M9 wires this into the
    state machine.
    """

    async def rerank(
        self,
        query: RetrievalQuery,
        candidates: Sequence[RankedCandidate],
        top_n: int,
    ) -> Sequence[RankedCandidate]: ...


__all__ = [
    "AccessPolicyFilter",
    "Bm25RetrieverProtocol",
    "DenseRetrieverProtocol",
    "QueryEmbedderProtocol",
    "RankedCandidate",
    "RerankerProtocol",
    "RetrievalCandidate",
    "RetrievalQuery",
    "RetrievalStageStats",
]
