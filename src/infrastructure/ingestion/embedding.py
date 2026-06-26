"""M7 `EmbeddingModelProtocol` deterministic-hash implementation.

The M7 ingestion path embeds every chunk into a 1536-dim vector
so the future M8 pgvector dense adapter can read the chunks
without further work. The Embedding Model is capability-based
per `PROJECT_STATUS.md` and `POLICIES.md`; M7 ships a
deterministic-hash stub because:

  - No production-grade SDK is pinned at M7 (V1 keeps the
    embedding capability un-selected until the Embedding Model
    capability is approved).
  - The stub is the canonical test embedder; the production
    embedder lands at M8 or M11 when the capability is bound.
  - The stub is reputable enough to populate the chunks with a
    reproducible 1536-dim vector that satisfies
    `chunks.embedding vector(1536)` and the pgvector codec.

Boundary contract:

| Concern                | Application sees             | Implementation lives                                          |
|------------------------|------------------------------|--------------------------------------------------------------|
| Embedding shape        | `list[float]` of length 1536 | deterministic hash, 1536 dims                                |
| Determinism            | reproducibility >= same input| sha256 seeded by text per-dim                                |
| Capability pinned      | not pinned                   | capability is `embedding_model` placeholder until M8/M11 binds |

When the Embedding Model capability is adopted at M8/M11, the
production code swaps the constructor inside the application
module's `__main__` / runtime wiring for the capability-bound
implementation. The application use case never imports a
specific SDK.
"""
from __future__ import annotations

import hashlib

from src.domain.ports.chunks import EMBEDDING_DIM
from src.domain.ports.ingestion import EmbeddingModelProtocol


class DeterministicHashEmbeddingModel(EmbeddingModelProtocol):
    """Deterministic 1536-dim embedding stub.

    Each dimension is drawn from sha256(text + ":dim-N"), with
    the first four bytes interpreted as a small integer. The
    resulting vector is reproducible across calls, stable across
    processes, and lies in `[-1, 1]`. The shape exceeds the
    required length because the test uses the full
    `EMBEDDING_DIM = 1536`.
    """

    def embed(self, text: str) -> list[float]:
        vector: list[float] = []
        for dim in range(EMBEDDING_DIM):
            digest = hashlib.sha256(
                f"{text}|dim-{dim}".encode("utf-8")
            ).digest()
            raw = int.from_bytes(digest[:4], "big") % 1000
            vector.append((raw / 500.0) - 1.0)
        return vector


__all__ = ["DeterministicHashEmbeddingModel"]
