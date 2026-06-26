"""M7 LlamaIndex chunker + hash embedder adapter tests.

Two distinct tests:

1. The LlamaIndex chunker produces at least one ChunkSegment
   for a long body, in ordinal order, with the right metadata.
2. The deterministic-hash embedder returns a vector of length
   `EMBEDDING_DIM` and is reproducible across calls.
"""
from __future__ import annotations

import pytest

from src.domain.ports.chunks import EMBEDDING_DIM
from src.infrastructure.ingestion import (
    DeterministicHashEmbeddingModel,
    LlamaIndexChunker,
    LlamaIndexChunkerConfig,
)


def test_llama_index_chunker_emits_ordinals_and_metadata():
    text = (
        "The retrieval pipeline combines dense and BM25 signals "
        "with cross-encoder reranking. The access decision runs "
        "before retrieval, after reranking, and at citation "
        "verification. RBAC binding is department plus clearance. "
        "Test regex guard pattern detection."
    )
    chunker = LlamaIndexChunker(
        LlamaIndexChunkerConfig(chunk_size=80, chunk_overlap=0)
    )
    segments = chunker.chunk(text)
    assert len(segments) >= 1
    for ordinal, segment in enumerate(segments):
        assert segment.ordinal == ordinal
        assert segment.text.strip()
        assert segment.metadata["ordinal"] == ordinal
        assert segment.metadata["length"] == len(segment.text)


def test_llama_index_chunker_with_empty_input_returns_empty():
    chunker = LlamaIndexChunker()
    assert chunker.chunk("") == []
    assert chunker.chunk("   \n\n   ") == []


def test_deterministic_hash_embedder_returns_correct_shape():
    embedder = DeterministicHashEmbeddingModel()
    vector = embedder.embed("hello world")
    assert len(vector) == EMBEDDING_DIM
    assert all(isinstance(v, float) for v in vector)


def test_deterministic_hash_embedder_is_reproducible():
    embedder = DeterministicHashEmbeddingModel()
    vector_a = embedder.embed("hello world")
    vector_b = embedder.embed("hello world")
    assert vector_a == vector_b
    # Different input -> different vector.
    vector_c = embedder.embed("goodbye world")
    assert vector_a != vector_c
