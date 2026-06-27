"""M8 infrastructure retrieval adapters (V1 capability adapters).

The M8 retrieval surface ships two V1 in-memory adapters —
`InMemoryDenseRetriever` and `InMemoryBm25Retriever` — plus an
identity cross-encoder reranker fallback. These satisfy the
M8 capability boundary while the framework adapters
(pgvector, pg_search, hosted rerankers) remain out-of-V1 stubs
until their owning adoption milestone.

The adapters here are the legitimate call site for the
`AccessPolicyFilter` projection: they translate the typed
projection into a filter that operates on the in-memory store
so the application use case's decision cannot be
circumvented.

V1 production note:

  - When pgvector + pg_search are adopted (M9+), the in-memory
    adapters are replaced by `PgVectorDenseRetriever` and
    `PgSearchBm25Retriever`. The protocol boundaries do not
    change.
"""
from src.infrastructure.retrieval.in_memory_dense import (
    InMemoryDenseRetriever,
    InMemoryDenseRow,
    InMemoryDenseStore,
)
from src.infrastructure.retrieval.in_memory_bm25 import (
    InMemoryBm25Document,
    InMemoryBm25Retriever,
    InMemoryBm25Store,
)
from src.infrastructure.retrieval.identity_reranker import (
    IdentityReranker,
)


__all__ = [
    "InMemoryDenseRetriever",
    "InMemoryDenseRow",
    "InMemoryDenseStore",
    "InMemoryBm25Document",
    "InMemoryBm25Retriever",
    "InMemoryBm25Store",
    "IdentityReranker",
]
