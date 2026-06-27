"""Tests for the M8 in-memory retrieval framework adapters.

Three tests:

1. The dense adapter applies the typed `AccessPolicyFilter`
   projection: rows in disallowed departments are filtered.
2. The BM25 adapter applies the same projection.
3. The reconstruction of a `RetrievalQuery` plus dense +
   BM25 + identity reranker mirrors the orchestrator's
   expected candidate flow without losing the
   `document_projection` on the candidate.
"""
from __future__ import annotations

import pytest

from src.application.auth.dto import AuthActor  # noqa: F401
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentProjection
from src.domain.ports.retrieval import (
    AccessPolicyFilter,
    RetrievalQuery,
)
from src.infrastructure.retrieval import (
    IdentityReranker,
    InMemoryBm25Retriever,
    InMemoryBm25Store,
    InMemoryBm25Document,
    InMemoryDenseRetriever,
    InMemoryDenseRow,
    InMemoryDenseStore,
)


def _query(*, allowed_departments=("engineering",), minimum_clearance="INTERNAL"):
    return RetrievalQuery(
        query_text="what is the runbook",
        top_k=5,
        access_filter=AccessPolicyFilter(
            allowed_departments=allowed_departments,
            minimum_clearance=minimum_clearance,
            decision_outcome=(True, "allowed"),
        ),
        correlation_id="corr-test",
    )


def _projection(department: str, clearance: Clearance):
    return DocumentProjection(
        department=department,
        required_clearance=clearance,
    )


async def test_in_memory_dense_applies_access_filter():
    store = InMemoryDenseStore()
    store.add(
        InMemoryDenseRow(
            chunk_id=10,
            document_id=100,
            ordinal=0,
            embedding=tuple([1.0] * 1536),
            document_projection=_projection(
                "engineering", Clearance.INTERNAL
            ),
        )
    )
    store.add(
        InMemoryDenseRow(
            chunk_id=11,
            document_id=101,
            ordinal=0,
            embedding=tuple([0.9] * 1536),
            document_projection=_projection("legal", Clearance.CONFIDENTIAL),
        )
    )
    adapter = InMemoryDenseRetriever(store)
    query = _query(allowed_departments=("engineering",), minimum_clearance="INTERNAL")
    candidates = await adapter.retrieve(query, embedding=[1.0] * 1536)
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.chunk_id == 10
    assert cand.document_projection is not None
    assert cand.document_projection.department == "engineering"


async def test_in_memory_bm25_respects_filter_and_tokenizes():
    store = InMemoryBm25Store()
    store.add(
        InMemoryBm25Document(
            chunk_id=20,
            document_id=200,
            ordinal=0,
            text="runbook for incident response",
            document_projection=_projection(
                "engineering", Clearance.INTERNAL
            ),
        )
    )
    store.add(
        InMemoryBm25Document(
            chunk_id=21,
            document_id=201,
            ordinal=0,
            text="legal counsel review",
            document_projection=_projection("legal", Clearance.CONFIDENTIAL),
        )
    )
    adapter = InMemoryBm25Retriever(store)
    query = _query(allowed_departments=("engineering",), minimum_clearance="INTERNAL")
    candidates = await adapter.retrieve(query)
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.chunk_id == 20
    assert cand.bm25_score is not None and cand.bm25_score > 0.0


async def test_identity_reranker_caps_top_n_and_preserves_projection():
    store = InMemoryDenseStore()
    for chunk_id in range(3):
        store.add(
            InMemoryDenseRow(
                chunk_id=chunk_id,
                document_id=100 + chunk_id,
                ordinal=0,
                embedding=tuple([0.5 + chunk_id * 0.1] * 1536),
                document_projection=_projection(
                    "engineering", Clearance.INTERNAL
                ),
            )
        )
    adapter = InMemoryDenseRetriever(store)
    query = _query()
    candidates = await adapter.retrieve(query, embedding=[0.5] * 1536)
    from src.domain.ports.retrieval import RankedCandidate

    ranked_inputs = [
        RankedCandidate(
            candidate=c, score=c.dense_score or 0.0, stage="fused"
        )
        for c in candidates
    ]
    reranker = IdentityReranker()
    reranked = await reranker.rerank(query, ranked_inputs, top_n=2)
    assert len(reranked) == 2
    for r in reranked:
        assert r.candidate.document_projection is not None
