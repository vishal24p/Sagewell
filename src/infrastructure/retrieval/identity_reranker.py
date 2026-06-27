"""Pass-through identity reranker for the M8 boundary.

The V1 cross-encoder reranker is a hosted-open-question
adoption (D-003); M8 ships an identity stub that simply
sorts by descending score and applies the `top_n` cap. The
real reranker adoption replaces this stub in its own
milestone; the application surface is unchanged.
"""
from __future__ import annotations

from typing import Sequence

from src.domain.ports.retrieval import (
    RankedCandidate,
    RerankerProtocol,
    RetrievalQuery,
)


class IdentityReranker(RerankerProtocol):
    """Default M8 reranker stub."""

    async def rerank(
        self,
        query: RetrievalQuery,
        candidates: Sequence[RankedCandidate],
        top_n: int,
    ) -> Sequence[RankedCandidate]:
        if top_n <= 0:
            return ()
        ordered = sorted(
            candidates,
            key=lambda c: -c.score,
        )[:top_n]
        return [
            RankedCandidate(
                candidate=c.candidate,
                score=c.score,
                stage="reranked",
            )
            for c in ordered
        ]
