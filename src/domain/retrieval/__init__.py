"""
V1 retrieval pure-function surface (M8).

This package holds framework-free retrieval primitives:
RRF fusion (`rrf.py`) and any pure projection helpers used
by the application-side orchestrator.

Framework-aware retrieval adapters live under
`src/infrastructure/retrieval/{dense,bm25,rrf,reranker}/`.
"""
from src.domain.retrieval.rrf import (
    DEFAULT_RRF_K,
    FusedCandidate,
    RankedItem,
    fuse,
)


__all__ = [
    "DEFAULT_RRF_K",
    "FusedCandidate",
    "RankedItem",
    "fuse",
]
