"""V1 RRF fusion (Reciprocal Rank Fusion).

A pure function used at the M8 boundary to fuse the dense
and BM25 ranked lists into a single fused list. The
algorithm is the canonical Reciprocal Rank Fusion:

  score(doc) = sum(1 / (K + rank_i)) for each retriever i
               where `rank_i` is the doc's 1-based rank in
               retriever i's list.

The constant K is a configuration knob (default 60 in the
project's prior art; pinned here at 60 deliberately) that
smooths the reciprocal-rank contribution from high-rank
documents. The function is pure and deterministic so the
M0 RBAC suite and the future RAGAS suite can exercise it
without I/O. The application boundary does not own rank
generation; it only fuses precomputed ranked lists.

Caller contract:

  - `fuse(dense_ranked, bm25_ranked, *, k=60)` accepts two
    ordered lists of `(chunk_id, document_id, score)`
    tuples in 1-based rank order. Both lists MAY contain
    the same chunk_id -> document_id pair (overlap-per-
    query is the canonical RRF trigger); each chunk_id ->
    document_id pair's fused score is then the sum of the
    reciprocal ranks across the two retrievers.
  - The fused list is sorted by `score DESC` and emitted.
    Ties are broken by `document_id ASC, chunk_id ASC` so
    the result is fully deterministic across orderings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


# Default reciprocal-rank K constant. The M8 orchestrator
# uses 60; tests are welcome to construct a `k=0` edge-case
# instance for boundary coverage.
DEFAULT_RRF_K: int = 60


@dataclass(frozen=True)
class RankedItem:
    """A single ranked entry passed to `fuse()`.

    `score` is the retriever's native score (dense cosine
    in [-1, 1] or BM25 from ParadeDB). M8's RRF ignores the
    raw score once ranks are computed; the score is preserved
    for observability rows in retrieval_logs.
    """
    chunk_id: int
    document_id: int
    score: float


@dataclass(frozen=True)
class FusedCandidate:
    """A M8 RRF output row."""
    chunk_id: int
    document_id: int
    fused_score: float
    dense_rank: int | None
    bm25_rank: int | None
    dense_score: float | None
    bm25_score: float | None


def _index(
    items: Iterable[RankedItem],
) -> dict[tuple[int, int], tuple[int, RankedItem]]:
    """Compute 1-based ranks and index by (document_id, chunk_id)."""
    out: dict[tuple[int, int], tuple[int, RankedItem]] = {}
    for rank, item in enumerate(items, start=1):
        if rank < 1:
            raise ValueError(f"rank must be >= 1; got {rank}")
        out[(item.document_id, item.chunk_id)] = (rank, item)
    return out


def fuse(
    dense_ranked: Iterable[RankedItem],
    bm25_ranked: Iterable[RankedItem],
    *,
    k: int = DEFAULT_RRF_K,
) -> list[FusedCandidate]:
    """Reciprocal Rank Fusion of the dense + BM25 ranked lists.

    The function is pure: no I/O, no datetime, no randomness.
    The fused list is sorted by `fused_score DESC`; ties are
    broken by `(document_id ASC, chunk_id ASC)`.
    """
    if k < 0:
        raise ValueError(
            f"RRF K constant must be non-negative; got {k}"
        )

    dense_index = _index(dense_ranked)
    bm25_index = _index(bm25_ranked)

    all_keys: set[tuple[int, int]] = set(dense_index) | set(bm25_index)
    fused: list[FusedCandidate] = []
    for key in sorted(all_keys):
        dense_pick = dense_index.get(key)
        bm25_pick = bm25_index.get(key)
        dense_rank, dense_item = (
            dense_pick if dense_pick is not None else (None, None)
        )
        bm25_rank, bm25_item = (
            bm25_pick if bm25_pick is not None else (None, None)
        )
        score = 0.0
        if dense_rank is not None:
            score += 1.0 / (k + dense_rank)
        if bm25_rank is not None:
            score += 1.0 / (k + bm25_rank)
        doc_id, chunk_id = key
        fused.append(
            FusedCandidate(
                chunk_id=chunk_id,
                document_id=doc_id,
                fused_score=score,
                dense_rank=dense_rank,
                bm25_rank=bm25_rank,
                dense_score=(
                    dense_item.score if dense_item is not None else None
                ),
                bm25_score=(
                    bm25_item.score if bm25_item is not None else None
                ),
            )
        )
    fused.sort(
        key=lambda c: (
            -c.fused_score,
            c.document_id,
            c.chunk_id,
        )
    )
    return fused


__all__ = [
    "DEFAULT_RRF_K",
    "FusedCandidate",
    "RankedItem",
    "fuse",
]
