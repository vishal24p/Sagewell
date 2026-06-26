"""M7 infrastructure ingestion adapters.

The M7 ingestion path uses two capability-based, framework-free
ports:

  - `DocumentChunkerProtocol` (from `src/domain/ports/ingestion.py`).
  - `EmbeddingModelProtocol` (from `src/domain/ports/ingestion.py`).

This infrastructure package ships the canonical LlamaIndex-
backed implementations. The production code path uses these.
The application use case under `src/application/ingestion/`
imports only the protocols, so a future capability-based
swap (a different chunker / a different embedder) does not
touch the application code at all.

The adapters in this package are the only place that imports
LlamaIndex at M7.
"""
from src.infrastructure.ingestion.chunker import (
    LlamaIndexChunker,
    LlamaIndexChunkerConfig,
)
from src.infrastructure.ingestion.embedding import (
    DeterministicHashEmbeddingModel,
)


__all__ = [
    "LlamaIndexChunker",
    "LlamaIndexChunkerConfig",
    "DeterministicHashEmbeddingModel",
]
