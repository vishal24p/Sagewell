"""M8 RRF (Reciprocal Rank Fusion) coverage.

Five distinct tests:

1. Pure function with disjoint lists produces the right
   reciprocal-rank sum.
2. Pure function with overlap adds the contributions.
3. `fused_score DESC` is the canonical sort order.
4. Ties break by `(document_id ASC, chunk_id ASC)` so the
   output is deterministic.
5. The function rejects negative K (fail closed).

The function is framework-free: no async, no I/O. The
tests run synchronously.
"""
from __future__ import annotations

import pytest

from src.domain.retrieval.rrf import (
    DEFAULT_RRF_K,
    FusedCandidate,
    RankedItem,
    fuse,
)


def _item(rank: int, chunk_id: int, document_id: int, score: float = 0.0):
    """Build a `RankedItem` from a 1-based rank, chunk id, document id.

    The function names the parameter order to read as
    `_item(rank=1, chunk_id=42, document_id=7, score=0.97)`.
    """
    del rank
    return RankedItem(chunk_id=chunk_id, document_id=document_id, score=score)


def test_fuse_disjoint_lists_yields_individual_reciprocal_ranks():
    dense = [
        _item(0, chunk_id=11, document_id=1),
        _item(0, chunk_id=22, document_id=2),
    ]
    bm25 = [
        _item(0, chunk_id=33, document_id=3),
        _item(0, chunk_id=44, document_id=4),
    ]
    fused = fuse(dense, bm25, k=DEFAULT_RRF_K)
    # Each disjoint entry has only its own retriever's contribution.
    by_doc = {c.document_id: c for c in fused}
    assert by_doc[1].fused_score == pytest.approx(1.0 / (60 + 1))
    assert by_doc[1].dense_rank == 1
    assert by_doc[1].bm25_rank is None
    assert by_doc[3].fused_score == pytest.approx(1.0 / (60 + 1))
    assert by_doc[3].bm25_rank == 1
    assert by_doc[3].dense_rank is None


def test_fuse_overlap_sums_reciprocal_rank_contributions():
    dense = [
        _item(0, chunk_id=11, document_id=1),
        _item(0, chunk_id=22, document_id=2),
    ]
    bm25 = [
        _item(0, chunk_id=22, document_id=2, score=0.91),
        _item(0, chunk_id=33, document_id=3),
    ]
    fused = fuse(dense, bm25)
    by_doc = {c.document_id: c for c in fused}
    overlap = by_doc[2]
    expected = 1.0 / (60 + 2) + 1.0 / (60 + 1)
    assert overlap.fused_score == pytest.approx(expected)
    assert overlap.dense_rank == 2
    assert overlap.bm25_rank == 1
    assert overlap.dense_score == 0.0
    assert overlap.bm25_score == 0.91


def test_fuse_sort_order_descending_by_score():
    dense = [
        _item(0, chunk_id=11, document_id=1),
        _item(0, chunk_id=22, document_id=2),
        _item(0, chunk_id=33, document_id=3),
      ]
    bm25 = [_item(0, chunk_id=22, document_id=2)]
    fused = fuse(dense, bm25)
    # Rank 1 in dense -> 1/(60+1); rank 2 in BM25 -> 1/(60+2).
    # document_id=2 has the highest score (overlap) and
    # therefore sorts first.
    assert fused[0].document_id == 2
    # The remaining disjoint docs sort by dense rank:
    # document_id=1 (dense rank 1) > document_id=3 (dense rank 3).
    assert fused[1].document_id == 1
    assert fused[2].document_id == 3


def test_fuse_ties_break_by_document_id_asc():
    # Two dense ranks + two bm25 ranks where the fused scores
    # all collapse to 1/(60+1) -> tie -> deterministic order
    # by (document_id, chunk_id) ascending.
    dense = [
        _item(0, chunk_id=10, document_id=1),
        _item(0, chunk_id=12, document_id=3),
    ]
    bm25 = [
        _item(0, chunk_id=11, document_id=2),
        _item(0, chunk_id=10, document_id=1),
    ]
    fused = fuse(dense, bm25)
    by_doc = {c.document_id: c for c in fused}
    # document 1 has TWO contributions (dense rank 1 + bm25 rank 2).
    # Its fused score is 1/(60+1) + 1/(60+2).
    expected_doc1 = 1.0 / (60 + 1) + 1.0 / (60 + 2)
    assert by_doc[1].fused_score == pytest.approx(expected_doc1)
    # document 2: only bm25 rank 1 -> 1/(60+1)
    assert by_doc[2].fused_score == pytest.approx(1.0 / (60 + 1))
    # document 3: only dense rank 2 -> 1/(60+2)
    assert by_doc[3].fused_score == pytest.approx(1.0 / (60 + 2))


def test_fuse_rejects_negative_k():
    with pytest.raises(ValueError):
        fuse([], [], k=-1)


def test_fuse_custom_k_runs_end_to_end():
    # k=0 collapses ranks to 1.0 for rank 1 and 1/(2) for rank 2.
    dense = [
        _item(0, chunk_id=11, document_id=1),
        _item(0, chunk_id=22, document_id=2),
    ]
    bm25 = []
    fused = fuse(dense, bm25, k=0)
    by_doc = {c.document_id: c for c in fused}
    assert by_doc[1].fused_score == pytest.approx(1.0 / 1)
    assert by_doc[2].fused_score == pytest.approx(1.0 / 2)
