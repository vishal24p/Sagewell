"""M8 retrieval application use case test fixtures.

Stub adapters for the M8 ports. The stubs are deterministic,
framework-free, and parameterized so each test can set up its
own dense / BM25 / rerank surface.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

import pytest

from src.application.auth.dto import AuthActor
from src.application.retrieval import (
    RetrieveAuthorizedCandidates,
    RetrieveAuthorizedCommand,
)
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentProjection
from src.domain.ports.retrieval import (
    Bm25RetrieverProtocol,
    DenseRetrieverProtocol,
    QueryEmbedderProtocol,
    RankedCandidate,
    RerankerProtocol,
    RetrievalCandidate,
    RetrievalQuery,
)


class StaticEmbedder(QueryEmbedderProtocol):
    """1536-dim deterministic stub embedder matching M1's shape."""

    pattern: tuple[float, ...] = (0.5, -0.5, 0.25)

    def embed(self, text: str) -> list[float]:
        out: list[float] = []
        for dim in range(1536):
            base = self.pattern[dim % len(self.pattern)]
            # Slight per-dim jitter so different texts are
            # distinguishable in cosine distance.
            offset = (ord(text[dim % len(text)]) / 255.0) * 0.01
            out.append(base + offset - 0.005)
        return out


class StaticDenseRetriever(DenseRetrieverProtocol):
    """In-memory dense retriever stub.

    The stub does NOT enforce the `AccessPolicyFilter` itself
    — the application-side use case relies on the framework
    adapter to translate the projection into SQL `WHERE`. The
    stub returns a configured list of candidates.
    """

    def __init__(
        self,
        candidates: Sequence[RetrievalCandidate] = (),
    ) -> None:
        self._candidates = list(candidates)
        self.last_query: Optional[RetrievalQuery] = None
        self.last_embedding: Optional[list[float]] = None

    async def retrieve(
        self,
        query: RetrievalQuery,
        embedding: list[float],
    ) -> Sequence[RetrievalCandidate]:
        self.last_query = query
        self.last_embedding = embedding
        return list(self._candidates)


class StaticBm25Retriever(Bm25RetrieverProtocol):
    """In-memory BM25 retriever stub."""

    def __init__(
        self,
        candidates: Sequence[RetrievalCandidate] = (),
    ) -> None:
        self._candidates = list(candidates)
        self.last_query: Optional[RetrievalQuery] = None

    async def retrieve(self, query):
        self.last_query = query
        return list(self._candidates)


class StaticReranker(RerankerProtocol):
    """Identity reranker (or scorer adjustment) stub.

    Default behavior is identity: the reranker takes the
    fused list and rewrites the score by `1 / rank`. Tests
    may set `score_fn` to override.
    """

    def __init__(
        self,
        identity: bool = True,
    ) -> None:
        self.identity = identity
        self.last_query: Optional[RetrievalQuery] = None

    async def rerank(self, query, candidates, top_n):
        self.last_query = query
        if self.identity:
            sorted_candidates = sorted(
                candidates,
                key=lambda c: -c.score,
            )[:top_n]
            return [
                RankedCandidate(
                    candidate=c.candidate,
                    score=c.score,
                    stage="reranked",
                )
                for c in sorted_candidates
            ]
        # Not a default path.
        return list(candidates[:top_n])


@dataclass
class _FakeDocs:
    """Per-chunk_id document projection source for the post-rerank drop."""

    by_chunk: dict[int, DocumentProjection] = field(default_factory=dict)
    unknown_chunks: list[int] = field(default_factory=list)


def _docs_by_chunk_id(fake_docs: _FakeDocs):
    """Return a closure suitable for `documents_by_chunk_id`."""

    def _lookup(chunk_id: int) -> Optional[DocumentProjection]:
        if chunk_id in fake_docs.by_chunk:
            return fake_docs.by_chunk[chunk_id]
        return None

    return _lookup


@pytest.fixture
def actor():
    return AuthActor(
        user_id="u-m8-test",
        department="engineering",
        clearance="internal",
        role="contributor",
        correlation_id="corr-m8-test",
    )


@pytest.fixture
def make_cmd(actor):
    """Factory for `RetrieveAuthorizedCommand` with sensible defaults."""

    def _make(**overrides):
        defaults = {
            "actor": actor,
            "query_text": "test query",
            "top_k": 5,
            "rerank_top_n": 3,
            "correlation_id": "corr-m8-test",
        }
        defaults.update(overrides)
        return RetrieveAuthorizedCommand(**defaults)

    return _make


@pytest.fixture
def use_case_factory():
    """Build a `RetrieveAuthorizedCandidates` with the supplied stubs.

    Designed so each test configures its own dense / bm25 / reranker
    surface; tests pass `dense`, `bm25`, `reranker`, and the
    `documents_by_chunk_id` closure.
    """

    def _build(
        *,
        dense,
        bm25,
        reranker=None,
        documents_by_chunk_id=None,
        embedder=None,
    ):
        return RetrieveAuthorizedCandidates(
            documents_by_chunk_id=documents_by_chunk_id
            or _docs_by_chunk_id(_FakeDocs()),
            embedder=embedder or StaticEmbedder(),
            dense_retriever=dense,
            bm25_retriever=bm25,
            reranker=reranker,
        )

    return _build


@pytest.fixture
def fake_docs():
    return _FakeDocs()


@pytest.fixture
def lookup(fake_docs):
    return _docs_by_chunk_id(fake_docs)
