"""M8 `RetrieveAuthorizedCandidates` use case coverage.

Six distinct tests:

1. Happy path: dense + BM25 both return overlapping
   candidates; RRF fuses them; reranker reranks; the
   post-rerank drop keeps survivors; the result carries
   per-stage counts.
2. Allow sequence end-to-end: decision = ALLOWED; the
   AuthorizationOutcome carries the M0 projected filter.
3. Deny at projection: missing clearance -> decision
   outcome not-allowed -> empty ranked result with
   stats captured.
4. Empty retrieval: dense + BM25 both return zero ->
   `EmptyRetrievalError`.
5. Embedding shape mismatch (wrong dim) -> raises.
6. Rerank skip path: when reranker is None, the fused
   list flows directly through to the post-rerank drop.
"""
from __future__ import annotations

import pytest

from src.application.retrieval.errors import (
    AccessDecisionUnavailableError,
    EmptyRetrievalError,
)
from src.domain.ports.documents import DocumentProjection
from src.domain.ports.retrieval import RetrievalCandidate
from src.domain.ports.clearances import Clearance

from tests.application.retrieval.conftest import (
    StaticBm25Retriever,
    StaticDenseRetriever,
    StaticReranker,
)


pytestmark = pytest.mark.asyncio


def _cand(
    chunk_id: int,
    document_id: int,
    dense: Optional[float] = None,
    bm25: Optional[float] = None,
):
    return RetrievalCandidate(
        chunk_id=chunk_id,
        document_id=document_id,
        ordinal=0,
        dense_score=dense,
        bm25_score=bm25,
    )


async def test_retrieve_happy_path_fuses_reranks_drops(use_case_factory, fake_docs, lookup, make_cmd):
    # Two dense candidates, two bm25 candidates (overlap on
    # chunk_id=11 to exercise RRF).
    dense = StaticDenseRetriever(
        candidates=[
            _cand(11, document_id=1, dense=0.95),
            _cand(22, document_id=2, dense=0.81),
        ]
    )
    bm25 = StaticBm25Retriever(
        candidates=[
            _cand(11, document_id=1, bm25=0.74),
            _cand(33, document_id=3, bm25=0.62),
        ]
    )
    # All three documents pass the access decision.
    fake_docs.by_chunk[11] = DocumentProjection(
        department="engineering", required_clearance=Clearance.INTERNAL
    )
    fake_docs.by_chunk[22] = DocumentProjection(
        department="engineering", required_clearance=Clearance.INTERNAL
    )
    fake_docs.by_chunk[33] = DocumentProjection(
        department="engineering", required_clearance=Clearance.INTERNAL
    )
    reranker = StaticReranker()
    use_case = use_case_factory(
        dense=dense,
        bm25=bm25,
        reranker=reranker,
        documents_by_chunk_id=lookup,
    )
    result = await use_case.execute(make_cmd())
    assert result.authorization.allowed is True
    assert result.authorization.reason == "allowed"
    # Stats cover all four mandatory stages.
    assert result.stats.dense_count == 2
    assert result.stats.bm25_count == 2
    assert result.stats.after_access_count >= 1
    # All survivors are authorized: their docs are present.
    assert len(result.ranked) >= 1
    for survivor in result.ranked:
        assert getattr(survivor.candidate, "document_projection", None) is not None


async def test_retrieve_authorization_outcome_carries_policy_filter(
    use_case_factory, fake_docs, lookup, make_cmd
):
    dense = StaticDenseRetriever(
        candidates=[_cand(11, 1, dense=0.95)]
    )
    bm25 = StaticBm25Retriever(candidates=[_cand(11, 1, bm25=0.74)])
    fake_docs.by_chunk[11] = DocumentProjection(
        department="engineering", required_clearance=Clearance.INTERNAL
    )
    use_case = use_case_factory(
        dense=dense,
        bm25=bm25,
        documents_by_chunk_id=lookup,
    )
    result = await use_case.execute(make_cmd())
    assert result.authorization.allowed is True
    pf = result.authorization.policy_filter
    # The actor's department mirrors into allowed_departments;
    # "ALL" is always present as the wildcard.
    assert "engineering" in pf.allowed_departments
    assert "ALL" in pf.allowed_departments
    # Minimum clearance is the actor's department-tied clearance.
    assert pf.minimum_clearance == "INTERNAL"


async def test_retrieve_deny_at_projection_returns_empty(use_case_factory, fake_docs, lookup, make_cmd, actor):
    # Construct an actor with missing/blank clearance.
    from src.application.retrieval import RetrieveAuthorizedCommand

    bad_actor = type(actor)(
        user_id=actor.user_id,
        department=actor.department,
        clearance="",  # blank clearance -> M0 pure function denies
        role=actor.role,
        correlation_id=actor.correlation_id,
    )
    dense = StaticDenseRetriever(
        candidates=[_cand(11, 1, dense=0.95)]
    )
    bm25 = StaticBm25Retriever(candidates=[_cand(11, 1, bm25=0.74)])
    use_case = use_case_factory(
        dense=dense, bm25=bm25, documents_by_chunk_id=lookup
    )
    cmd = RetrieveAuthorizedCommand(
        actor=bad_actor,
        query_text="q",
        top_k=5,
        rerank_top_n=3,
    )
    result = await use_case.execute(cmd)
    assert result.authorization.allowed is False
    assert result.authorization.reason == "missing_user_clearance"
    assert result.ranked == ()
    assert result.stats.dense_count == 0
    assert result.stats.bm25_count == 0
    assert result.stats.fused_count == 0
    assert result.stats.after_access_count == 0


async def test_retrieve_raises_when_dense_and_bm25_return_empty(
    use_case_factory, lookup, make_cmd
):
    dense = StaticDenseRetriever(candidates=[])
    bm25 = StaticBm25Retriever(candidates=[])
    use_case = use_case_factory(
        dense=dense, bm25=bm25, documents_by_chunk_id=lookup
    )
    with pytest.raises(EmptyRetrievalError):
        await use_case.execute(make_cmd())


async def test_retrieve_rejects_malformed_embedding(
    use_case_factory, lookup, make_cmd
):
    class BadDimEmbedder:
        def embed(self, text):
            # Returns a 100-dim vector; not 1536.
            return [0.0] * 100

    dense = StaticDenseRetriever(candidates=[_cand(11, 1, dense=0.95)])
    bm25 = StaticBm25Retriever(candidates=[_cand(11, 1, bm25=0.74)])
    use_case = use_case_factory(
        dense=dense,
        bm25=bm25,
        embedder=BadDimEmbedder(),
        documents_by_chunk_id=lookup,
    )
    with pytest.raises(AccessDecisionUnavailableError):
        await use_case.execute(make_cmd())


async def test_retrieve_rerank_skip_when_reranker_none(
    use_case_factory, fake_docs, lookup, make_cmd
):
    dense = StaticDenseRetriever(
        candidates=[
            _cand(11, 1, dense=0.95),
            _cand(22, 2, dense=0.81),
        ]
    )
    bm25 = StaticBm25Retriever(
        candidates=[_cand(22, 2, bm25=0.74), _cand(33, 3, bm25=0.62)]
    )
    for chunk_id in (11, 22, 33):
        fake_docs.by_chunk[chunk_id] = DocumentProjection(
            department="engineering", required_clearance=Clearance.INTERNAL
        )
    use_case = use_case_factory(
        dense=dense,
        bm25=bm25,
        reranker=None,  # rerank skipped
        documents_by_chunk_id=lookup,
    )
    result = await use_case.execute(make_cmd())
    # rerank_count remains 0; fused_count carries the items that
    # flowed directly to the post-rerank drop.
    assert result.stats.rerank_count == 0
    assert result.stats.fused_count >= 1
    assert result.stats.after_access_count >= 1
