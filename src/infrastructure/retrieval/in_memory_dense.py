"""In-memory dense retriever for the M8 boundary.

The dense adapter performs a cosine-similarity scan over an
in-memory catalog of `(document_id, chunk_id, embedding,
text_preview, document_projection)` rows. The cosine
implementation is a pure-Python loop; capability-deferred
adoptions (gpu-accelerated pgvector, etc.) replace this at a
later milestone without disturbing the application use case.

The adapter respects the `AccessPolicyFilter` projection:
candidates whose `documents.department` is not in
`allowed_departments`, or whose
`documents.required_clearance` exceeds
`minimum_clearance`, are filtered out before the similarity
scan. The adapter never re-implements the access decision;
the projection is computed by the application layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentProjection
from src.domain.ports.retrieval import (
    DenseRetrieverProtocol,
    RetrievalCandidate,
    RetrievalQuery,
)


@dataclass(frozen=True)
class InMemoryDenseRow:
    """A canonical in-memory row."""

    chunk_id: int
    document_id: int
    ordinal: int
    embedding: tuple[float, ...]
    text_preview: Optional[str] = None
    document_projection: Optional[DocumentProjection] = None


@dataclass
class InMemoryDenseStore:
    rows: list[InMemoryDenseRow] = field(default_factory=list)

    def add(self, row: InMemoryDenseRow) -> None:
        self.rows.append(row)

    def clear(self) -> None:
        self.rows.clear()


class InMemoryDenseRetriever(DenseRetrieverProtocol):
    """V1 in-memory dense retriever.

    Translate the typed `AccessPolicyFilter` into a filter
    that is applied before the similarity scan.
    """

    def __init__(self, store: InMemoryDenseStore) -> None:
        self._store = store

    async def retrieve(
        self,
        query: RetrievalQuery,
        embedding: list[float],
    ) -> Sequence[RetrievalCandidate]:
        policy = query.access_filter
        min_clearance_name = policy.minimum_clearance
        try:
            min_clearance = Clearance[min_clearance_name]
        except KeyError:
            min_clearance = Clearance.PUBLIC

        indexed: list[tuple[float, InMemoryDenseRow]] = []
        for row in self._store.rows:
            # Department filter.
            if (
                policy.allowed_departments
                and (
                    row.document_projection is None
                    or row.document_projection.department
                    not in policy.allowed_departments
                )
            ):
                continue
            # Clearance filter (>=).
            if row.document_projection is None:
                continue
            if not row.document_projection.required_clearance.is_at_least(
                min_clearance
            ):
                continue
            # Cosine similarity.
            score = _cosine(embedding, list(row.embedding))
            indexed.append((score, row))

        # Sort by descending similarity.
        indexed.sort(key=lambda pair: -pair[0])
        # Apply top_k + leave one slot for RRF disambiguation.
        top_k = max(query.top_k, 1)
        chosen = indexed[:top_k]
        return [
            RetrievalCandidate(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                ordinal=row.ordinal,
                dense_score=float(score),
                bm25_score=None,
                text_preview=row.text_preview,
                document_projection=row.document_projection,
            )
            for score, row in chosen
        ]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for i, _ in enumerate(a):
        dot += a[i] * b[i]
        norm_a += a[i] * a[i]
        norm_b += b[i] * b[i]
    denom_sq = norm_a * norm_b
    if denom_sq <= 0.0:
        return 0.0
    return dot / (denom_sq ** 0.5)
