"""M15 real-corpus pipeline fixture + helper.

Drives the V1 ingestion (M7) -> retrieval (M8) -> citation
verification (M9) pipeline against a real, on-disk corpus of
markdown documents. The corpus path is resolved via::

    REAL_CORPUS_DIR=<path>          (default: <repo>/en/)
    REAL_CORPUS_LIMIT=int            (default: 25)

The corpus is intentionally NOT committed. The .gitignore entry
at ``en/`` preserves the rule "do not push the data".

The fixture is a single ``real_corpus_pipeline`` async
generator that returns a populated ``RealCorpusPipeline``
dataclass; the architectural rest follows the M8/M9 fixtures
the V1 repository already ships (deterministic embedder,
fixed chunker, in-memory repos).

For end-to-end pipeline assertions the test imports the
``build_*`` helpers below; each helper wires the canonical M7
use case or the M8/M9 orchestrators onto the populated
in-memory V1 repositories.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


from src.application.auth.dto import AuthActor
from src.domain.ports.chunks import EMBEDDING_DIM
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentProjection
from src.application.audit_event.clock import SystemClock
from src.application.audit_event.record import RecordAuditEvent
from src.infrastructure.ingestion.chunker import LlamaIndexChunker
from src.infrastructure.ingestion.embedding import (
    DeterministicHashEmbeddingModel,
)
from src.infrastructure.repositories.in_memory.audit_logs import (
    InMemoryAuditLogRepository,
)
from src.infrastructure.repositories.in_memory.chunks import (
    InMemoryChunkRepository,
)
from src.infrastructure.repositories.in_memory.documents import (
    InMemoryDocumentRepository,
)
from src.infrastructure.repositories.in_memory.retrieval_logs import (
    InMemoryRetrievalLogRepository,
)
from src.infrastructure.retrieval.in_memory_bm25 import (
    InMemoryBm25Document,
    InMemoryBm25Retriever,
    InMemoryBm25Store,
)
from src.infrastructure.retrieval.in_memory_dense import (
    InMemoryDenseRetriever,
    InMemoryDenseRow,
    InMemoryDenseStore,
)


DEFAULT_CORPUS_DIR = Path(__file__).resolve().parents[2] / "en"
DEFAULT_LIMIT = 25
REAL_CORPUS_DIR_ENV = "REAL_CORPUS_DIR"
REAL_CORPUS_LIMIT_ENV = "REAL_CORPUS_LIMIT"
SOURCE_SYSTEM = "real-corpus"
DEFAULT_DEPARTMENT = "engineering"
ACTOR_USER_ID = "real-corpus-pipeline-actor"


@dataclass
class RealCorpusPipeline:
    """Snapshot returned by ``make_real_corpus_pipeline``."""

    corpus_dir: Path
    sources: tuple[str, ...]
    document_ids: dict[str, int] = field(default_factory=dict)
    chunk_count: int = 0
    actor: AuthActor = field(
        default_factory=lambda: AuthActor(
            user_id=ACTOR_USER_ID,
            department=DEFAULT_DEPARTMENT,
            clearance=Clearance.INTERNAL.name,
            role="employee",
            correlation_id="real-corpus-correlation",
        )
    )
    documents: InMemoryDocumentRepository | None = None
    chunks: InMemoryChunkRepository | None = None
    dense_retriever: InMemoryDenseRetriever | None = None
    bm25_retriever: InMemoryBm25Retriever | None = None


def resolved_corpus_dir() -> Path:
    """Resolve the on-disk corpus directory.

    Order:
      1. ``REAL_CORPUS_DIR`` env var (preferred for CI).
      2. ``<repo>/en/`` (the common dev case; the path the
         user dropped at the repository root as data, not code).
    """
    env = os.environ.get(REAL_CORPUS_DIR_ENV)
    candidate = Path(env) if env else DEFAULT_CORPUS_DIR
    return candidate.resolve()


def pick_corpus_paths(corpus_dir: Path, limit: int) -> tuple[Path, ...]:
    """Deterministically pick the first ``limit`` markdown files."""
    if not corpus_dir.exists():
        return ()
    return tuple(sorted(p for p in corpus_dir.rglob("*.md") if p.is_file())[:limit])


def corpus_limit() -> int:
    """Resolve the corpus limit, defaulting to ``DEFAULT_LIMIT``."""
    env = os.environ.get(REAL_CORPUS_LIMIT_ENV)
    return int(env) if env else DEFAULT_LIMIT


def make_real_corpus_actor() -> AuthActor:
    """Canonical actor for the M15 release-gate test."""
    return AuthActor(
        user_id=ACTOR_USER_ID,
        department=DEFAULT_DEPARTMENT,
        clearance=Clearance.INTERNAL.name,
        role="employee",
        correlation_id="real-corpus-correlation",
    )


def heuristic_clearance(path: Path) -> Clearance:
    """Pick a clearance for the document via path heuristic.

    `training/` and `community/` content are PUBLIC; everything
    else is INTERNAL. Heuristic is intentionally simple; the
    test asserts the pipeline accepts the result.
    """
    parts = {p.lower() for p in path.parts}
    if parts & {"training", "community"}:
        return Clearance.PUBLIC
    return Clearance.INTERNAL


def _ensure_embedding_dim(embedding: list[float]) -> list[float]:
    if len(embedding) != EMBEDDING_DIM:
        raise ValueError(
            f"embedder returned {len(embedding)} dims; expected {EMBEDDING_DIM}"
        )
    return list(embedding)


async def _build_chunks_for_document(
    *,
    text: str,
    document_id: int,
    chunker: LlamaIndexChunker,
    embedder: DeterministicHashEmbeddingModel,
) -> tuple[list, int]:
    """Chunk + embed. Returns (drafts, total_count)."""
    segments = chunker.chunk(text)
    drafts = []
    for segment in segments:
        drafts.append(
            _draft(
                document_id=document_id,
                text=segment.text,
                ordinal=segment.ordinal,
                metadata=segment.metadata,
                embedding=embedder,
            )
        )
    return drafts, len(drafts)


def _draft(*, document_id: int, text: str, ordinal: int, metadata: dict, embedding):
    from src.domain.ports.chunks import ChunkDraft

    return ChunkDraft(
        document_id=document_id,
        ordinal=ordinal,
        text=text,
        text_search=text,
        embedding=_ensure_embedding_dim(embedding.embed(text)),
        metadata=metadata,
        token_count=None,
    )


async def make_real_corpus_pipeline() -> RealCorpusPipeline:
    """Compose the V1 pipeline against the real corpus.

    Imports the V1 ``IngestDocument`` use case inline so the
    fixture respects the canonical M7 command shape. After
    ingest, the in-memory chunks are projected into the M8
    dense + BM25 stores so a single M8 ``Retrieve`` call can be
    tested without re-running the embedder.
    """
    corpus_dir = resolved_corpus_dir()
    if not corpus_dir.exists():
        import pytest

        pytest.skip(
            f"{REAL_CORPUS_DIR_ENV} not present: {corpus_dir}. "
            f"Set {REAL_CORPUS_DIR_ENV} or populate ./en/"
        )
    paths = pick_corpus_paths(corpus_dir, corpus_limit())
    if not paths:
        import pytest

        pytest.skip(f"No .md files under {corpus_dir}")

    documents = InMemoryDocumentRepository()
    chunks = InMemoryChunkRepository()
    audit_repo = InMemoryAuditLogRepository()
    retrieval_log_repo = InMemoryRetrievalLogRepository()
    clock = SystemClock()
    record_audit_event = RecordAuditEvent(audit_repo, clock=clock)

    from src.application.ingestion.ingest import (
        IngestDocument,
        IngestDocumentCommand,
    )

    use_case = IngestDocument(
        documents=documents,
        chunks=chunks,
        chunker=LlamaIndexChunker(),
        embedder=DeterministicHashEmbeddingModel(),
        record_audit_event=record_audit_event,
        clearance_enum=Clearance,
    )

    actor = make_real_corpus_actor()
    sources: list[str] = []
    document_ids: dict[str, int] = {}
    chunk_count = 0
    chunker = LlamaIndexChunker()
    embedder = DeterministicHashEmbeddingModel()

    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text or not text.strip():
            continue
        uri = str(path)
        title = path.stem.replace("_", " ").replace("-", " ").strip() or path.name
        cmd = IngestDocumentCommand(
            actor=actor,
            source_system=SOURCE_SYSTEM,
            source_id=uri,
            title=title,
            uri=uri,
            department=DEFAULT_DEPARTMENT,
            required_clearance=heuristic_clearance(path),
            content=text,
            metadata={"uri": uri, "size": len(text)},
            correlation_id=actor.correlation_id,
        )
        try:
            result = await use_case.execute(cmd)
        except Exception:
            # Single-file failure does not abort the pipeline;
            # surface in the test through audit-log count instead.
            continue
        if result.document_id is None:
            continue
        sources.append(uri)
        document_ids[uri] = int(result.document_id)
        chunk_count += int(result.inserted_chunk_count or 0)

    pipeline = RealCorpusPipeline(
        corpus_dir=corpus_dir,
        sources=tuple(sources),
        document_ids=document_ids,
        chunk_count=chunk_count,
        actor=actor,
        documents=documents,
        chunks=chunks,
    )

    dense_store = InMemoryDenseStore()
    bm25_store = InMemoryBm25Store()
    for chunk in chunks._chunks.values():
        if chunk.status.name != "ACTIVE":
            continue
        doc = documents._documents.get(chunk.document_id)
        if doc is None:
            continue
        projection = DocumentProjection(
            department=doc.department,
            required_clearance=Clearance[doc.required_clearance.name],
        )
        dense_store.add(
            InMemoryDenseRow(
                chunk_id=int(chunk.id),
                document_id=int(chunk.document_id),
                ordinal=int(chunk.ordinal),
                embedding=tuple(float(v) for v in chunk.embedding),
                text_preview=chunk.text[:160],
                document_projection=projection,
            )
        )
        bm25_store.add(
            InMemoryBm25Document(
                chunk_id=int(chunk.id),
                document_id=int(chunk.document_id),
                ordinal=int(chunk.ordinal),
                text=chunk.text,
                text_preview=chunk.text[:160],
                document_projection=projection,
            )
        )
    pipeline.dense_retriever = InMemoryDenseRetriever(dense_store)
    pipeline.bm25_retriever = InMemoryBm25Retriever(bm25_store)
    return pipeline


def build_retrieve_orchestrator(
    pipeline: RealCorpusPipeline,
    documents_by_chunk_id,
):
    """Wire the M8 orchestrator against the populated retrievers.

    `documents_by_chunk_id` is the post-rerank projector the
    orchestrator needs to materialize each surviving candidate's
    `document_projection`. The fixture provides a thin callable
    bridge so the orchestrator stays free of repository imports.
    """
    from src.application.retrieval.retrieve import (
        RetrieveAuthorizedCandidates,
    )
    from src.infrastructure.retrieval.identity_reranker import (
        IdentityReranker,
    )

    return RetrieveAuthorizedCandidates(
        documents_by_chunk_id=documents_by_chunk_id,
        dense_retriever=pipeline.dense_retriever,
        bm25_retriever=pipeline.bm25_retriever,
        reranker=IdentityReranker(),
        embedder=DeterministicHashEmbeddingModel(),
    )


def build_verify_citations(documents_by_id=None):
    """Construct the M9 VerifyCitations use case.

    `documents_by_id` resolves the canonical Document row
    (or `None` for a missing citation). When the citation
    already carries a `document_projection`, M9 prefers
    that projection and avoids the lookup. The callable
    is still required by the constructor signature even
    when unused.
    """
    from src.application.citations.verify import VerifyCitations

    def _resolve(document_id: int):
        if documents_by_id is None:
            return None
        return documents_by_id.get(document_id)

    return VerifyCitations(documents_by_id=_resolve)


__all__ = [
    "ACTOR_USER_ID",
    "DEFAULT_DEPARTMENT",
    "DEFAULT_LIMIT",
    "REAL_CORPUS_DIR_ENV",
    "REAL_CORPUS_LIMIT_ENV",
    "SOURCE_SYSTEM",
    "RealCorpusPipeline",
    "build_retrieve_orchestrator",
    "build_verify_citations",
    "corpus_limit",
    "heuristic_clearance",
    "make_real_corpus_actor",
    "make_real_corpus_pipeline",
    "pick_corpus_paths",
    "resolved_corpus_dir",
]
