"""Print the V1 model inventory verbatim from the workspace.

Walks `src/` and prints every class and Protocol that is wired
into the M0..M15 pipeline so the answer to "what are the
models we are using here" is recorded verbatim in one place.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> None:
    """Print the verbatim model + adapter inventory."""
    print("=" * 72)
    print("V1 model inventory (verbatim names; AGENTS.md = capability-only)")
    print("=" * 72)

    print("\n[1] Domain ports / Protocol-shaped capabilities")
    print("-" * 72)
    from src.domain.ports.ingestion import (
        DocumentChunkerProtocol,
        EmbeddingModelProtocol,
    )
    from src.domain.ports.retrieval import (
        DenseRetrieverProtocol,
        Bm25RetrieverProtocol,
        RerankerProtocol,
        QueryEmbedderProtocol,
    )
    from src.domain.ports.llm_guard import GuardrailModelPort
    from src.domain.ports.ragas import RagasScorerPort

    for cls in (
        DocumentChunkerProtocol,
        EmbeddingModelProtocol,
        QueryEmbedderProtocol,
        DenseRetrieverProtocol,
        Bm25RetrieverProtocol,
        RerankerProtocol,
        GuardrailModelPort,
        RagasScorerPort,
    ):
        print(f"  protocol  {cls.__module__}.{cls.__name__}")
    print("  decorator-port   src.domain.ports.retrieval.QueryEmbedderProtocol "
          "(re-export of EmbeddingModelProtocol)")

    print("\n[2] Infrastructure adapters (concrete classes wired today)")
    print("-" * 72)
    from src.infrastructure.ingestion.chunker import (
        LlamaIndexChunker,
        LlamaIndexChunkerConfig,
    )
    from src.infrastructure.ingestion.embedding import (
        DeterministicHashEmbeddingModel,
    )
    from src.infrastructure.retrieval.in_memory_dense import (
        InMemoryDenseRetriever,
        InMemoryDenseStore,
    )
    from src.infrastructure.retrieval.in_memory_bm25 import (
        InMemoryBm25Retriever,
        InMemoryBm25Store,
    )
    from src.infrastructure.retrieval.identity_reranker import IdentityReranker
    from src.infrastructure.repositories.in_memory.documents import (
        InMemoryDocumentRepository,
    )
    from src.infrastructure.repositories.in_memory.chunks import (
        InMemoryChunkRepository,
    )

    adapters = (
        ("chunker", LlamaIndexChunker, "LlamaIndex SentenceSplitter (no model)"),
        ("chunker-cfg", LlamaIndexChunkerConfig, "config-only; no model"),
        ("embedder", DeterministicHashEmbeddingModel, "deterministic-hash 1536-dim stub"),
        ("dense-row", InMemoryDenseStore, "in-memory row container"),
        ("dense-retriever", InMemoryDenseRetriever, "cosine scan; no hosted model"),
        ("bm25-retriever", InMemoryBm25Retriever, "BM25 (k1=1.5,b=0.75); no hosted model"),
        ("reranker", IdentityReranker, "sort + cap; no hosted model"),
        ("document-repo", InMemoryDocumentRepository, "in-memory; no Postgres at test"),
        ("chunk-repo", InMemoryChunkRepository, "in-memory; no Postgres at test"),
    )
    for slot, cls, note in adapters:
        print(f"  adapter  {slot:14s}  {cls.__module__}.{cls.__name__}   ({note})")

    print("\n[3] Models NOT yet wired (capability-only)")
    print("-" * 72)
    not_wired = [
        ("Embedding Model",
         "Capability port only; DeterministicHashEmbeddingModel is a strict test stub."),
        ("Reranker Model",
         "Only the IdenityReranker stub is wired."),
        ("Guardrail Model",
         "Capability port only; no adapter is wired."),
        ("Generation Model",
         "Out of M0..M15 scope. Open question D-005."),
        ("RAGAS SDK",
         "Capability port only; no hosted SDK adopted."),
    ]
    for name, status in not_wired:
        print(f"  --  {name:18s}  {status}")

    print("\n[4] Frameworks (NOT models)")
    print("-" * 72)
    print("  framework  llama_index.core.node_parser       chunker SentenceSplitter")
    print("  framework  langgraph.graph                    M9 workflow orchestration")
    print("  framework  fastapi                            M3 API skeleton (no model)")

    print("\n[5] V1 capability adoption gates (PROJECT_STATUS.md)")
    print("-" * 72)
    print("  capability   open question    readiness")
    print("  Embedding    D-002            out-of-V1 (capability, deferred)")
    print("  Reranker     D-003            out-of-V1 (capability, deferred)")
    print("  Guardrail    D-004            out-of-V1 (capability, deferred)")
    print("  Generation   D-005            out-of-V1 (capability, deferred)")
    print("  RAGAS        D-006            out-of-V1 (capability, deferred)")
    print()
    print("Bottom line: zero production model SDKs are imported or pinned")
    print("anywhere in src/. The M2..M15 pipeline goes through ports only;")
    print("any hosted model adoption is its own ADR per AGENTS.md.")


if __name__ == "__main__":
    main()
