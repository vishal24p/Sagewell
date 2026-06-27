"""In-memory BM25 retriever for the M8 boundary.

The BM25 adapter scores documents by a simplified BM25 over
an in-memory catalog. The implementation uses the canonical
BM25 formula with `k1=1.5`, `b=0.75` (ParadeDB defaults;
locked per the M8 capability surface). The actual V1 adoption
of `pg_search` / ParadeDB replaces this stub at the
appropriate milestone; the application use case does not see
that swap.

The adapter respects the `AccessPolicyFilter` projection the
same way the dense adapter does. Both adapters receive the
exact same projection and apply the exact same filter so the
dense / BM25 candidate sets stay aligned.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentProjection
from src.domain.ports.retrieval import (
    Bm25RetrieverProtocol,
    RetrievalCandidate,
    RetrievalQuery,
)


# Standard BM25 hyperparameters aligned with ParadeDB / pg_search.
_BM25_K1 = 1.5
_BM25_B = 0.75


@dataclass(frozen=True)
class InMemoryBm25Document:
    """Lexical corpus row."""

    chunk_id: int
    document_id: int
    ordinal: int
    text: str
    text_preview: Optional[str] = None
    document_projection: Optional[DocumentProjection] = None


@dataclass
class InMemoryBm25Store:
    docs: list[InMemoryBm25Document] = field(default_factory=list)

    def add(self, doc: InMemoryBm25Document) -> None:
        self.docs.append(doc)

    def clear(self) -> None:
        self.docs.clear()


class InMemoryBm25Retriever(Bm25RetrieverProtocol):
    """V1 in-memory BM25 retriever."""

    def __init__(
        self,
        store: InMemoryBm25Store,
        *,
        k1: float = _BM25_K1,
        b: float = _BM25_B,
    ) -> None:
        self._store = store
        self._k1 = k1
        self._b = b

    async def retrieve(
        self,
        query: RetrievalQuery,
    ) -> Sequence[RetrievalCandidate]:
        policy = query.access_filter
        min_clearance_name = policy.minimum_clearance
        try:
            min_clearance = Clearance[min_clearance_name]
        except KeyError:
            min_clearance = Clearance.PUBLIC

        # Compute idf on the filtered set only.
        filtered = [
            doc
            for doc in self._store.docs
            if doc.document_projection is not None
            and (
                not policy.allowed_departments
                or doc.document_projection.department
                in policy.allowed_departments
            )
            and doc.document_projection.required_clearance.is_at_least(
                min_clearance
            )
        ]
        if not filtered:
            return ()

        docs_terms = [_tokenize(doc.text) for doc in filtered]
        q_terms = _tokenize(query.query_text)
        if not q_terms:
            return ()
        df: dict[str, int] = {}
        for terms in docs_terms:
            unique = set(terms)
            for term in q_terms:
                if term in unique:
                    df[term] = df.get(term, 0) + 1
        n = len(filtered)
        avgdl = sum(len(terms) for terms in docs_terms) / n

        scored: list[tuple[float, InMemoryBm25Document]] = []
        for doc, terms in zip(filtered, docs_terms):
            tf: dict[str, int] = {}
            for term in terms:
                tf[term] = tf.get(term, 0) + 1
            score = _bm25_score(
                q_terms, tf, df, n, avgdl, self._k1, self._b
            )
            if score > 0.0:
                scored.append((score, doc))

        scored.sort(key=lambda pair: -pair[0])
        top_k = max(query.top_k, 1)
        chosen = scored[:top_k]
        return [
            RetrievalCandidate(
                chunk_id=doc.chunk_id,
                document_id=doc.document_id,
                ordinal=doc.ordinal,
                dense_score=None,
                bm25_score=float(score),
                text_preview=doc.text_preview,
                document_projection=doc.document_projection,
            )
            for score, doc in chosen
        ]


def _tokenize(text: str) -> list[str]:
    return [tok for tok in text.lower().split() if tok]


def _bm25_score(
    query_terms: list[str],
    tf: dict[str, int],
    df: dict[str, int],
    n: int,
    avgdl: float,
    k1: float,
    b: float,
) -> float:
    import math

    score = 0.0
    dl = sum(tf.values())
    for term in query_terms:
        if dl <= 0:
            break
        f = tf.get(term, 0)
        if f <= 0:
            continue
        n_q = df.get(term, 0)
        idf = math.log(1 + (n - n_q + 0.5) / (n_q + 0.5))
        numerator = f * (k1 + 1)
        denominator = f + k1 * (1 - b + b * dl / max(avgdl, 1e-9))
        score += idf * numerator / denominator
    return score
