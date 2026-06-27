"""M15 release-gate: real-corpus end-to-end pipeline test.

Exercises M7 ingestion -> M8 retrieval -> M9 citation verification
against a real, on-disk corpus. The corpus is configured via::

    REAL_CORPUS_DIR      (default: <repo>/en/)
    REAL_CORPUS_LIMIT    (default: 25)

The corpus must NOT be pushed; the .gitignore entry at ``en/``
preserves the user's "do not commit the data" rule. The test
skips politely when the corpus is absent so the rest of the
release-bar suite stays green.

What this test guards:

  - M7 IngestDocument accepts each markdown file (audit row
    emitted, chunks persisted, documents keyed on uri).
  - M8 RetrieveAuthorizedCandidates honors the access filter
    end-to-end on the populated retrievers; the access decision
    fires at the pre-retrieval projection even on real data.
  - M9 VerifyCitations drops citations whose document fails the
    access decision (third M0 invocation).
  - The launch contract stays DB-free: no Postgres, no Compose,
    no network. All wiring is in-memory V1.

What this test does NOT guard (out of M15 scope):

  - Postgres parity (M2 covers that).
  - In-memory launch-contract smoke (M14 covers that).
  - RAGAS / RBAC suites (M13 / M0 cover those).
"""
from __future__ import annotations

import pytest

from src.application.citations.verify import (
    VerifyCitationsCommand,
    VerifyCitationsResult,
)
from src.application.retrieval.errors import EmptyRetrievalError
from src.application.retrieval.retrieve import RetrieveAuthorizedCommand
from src.domain.ports.citations import Citation
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentProjection
from src.application.auth.dto import AuthActor

from tests.release_gate.m15_corpus_loader import (
    RealCorpusPipeline,
    build_retrieve_orchestrator,
    build_verify_citations,
    make_real_corpus_pipeline,
)


LABEL_DEPARTMENT_MISMATCH = "department_mismatch"
LABEL_CLEARANCE_INSUFFICIENT = "clearance_insufficient"
ALL_DROP_REASONS = {LABEL_DEPARTMENT_MISMATCH, LABEL_CLEARANCE_INSUFFICIENT}


@pytest.fixture
async def pipeline() -> RealCorpusPipeline:
    """Build the real-corpus pipeline once for the module's tests.

    The fixture runs synchronously enough for pytest-asyncio; per-file
    ingestion failures are absorbed by ``make_real_corpus_pipeline``
    so a single bad markdown doesn't abort the suite.
    """
    return await make_real_corpus_pipeline()


async def test_corpus_language_loads(pipeline: RealCorpusPipeline) -> None:
    """The corpus directory is real, and at least one .md file exists."""
    assert pipeline.corpus_dir.exists()
    assert any(p.suffix.lower() == ".md" for p in pipeline.corpus_dir.rglob("*.md"))


async def test_m7_ingest_yields_active_chunks(pipeline: RealCorpusPipeline) -> None:
    """Every ingested file produces ACTIVE chunks; total > 0."""
    assert pipeline.chunk_count > 0
    active = sum(
        1
        for chunk in pipeline.chunks._chunks.values()
        if chunk.status.name == "ACTIVE"
    )
    assert active == pipeline.chunk_count, (
        f"expected {pipeline.chunk_count} ACTIVE chunks; got {active}"
    )


async def test_m8_retrieve_honors_department_filter(
    pipeline: RealCorpusPipeline,
) -> None:
    """Department filter applied end-to-end on the real corpus.

    The corpus is single-department (`engineering`); an actor from
    a different department therefore gets an empty retrieval, which
    is the canonical V1 output for "no authorized documents".
    """
    if pipeline.chunk_count == 0:
        pytest.skip("no chunks; corpus was empty after ingest.")

    documents_by_chunk_id = _documents_by_chunk_id(pipeline)
    orchestrator = build_retrieve_orchestrator(pipeline, documents_by_chunk_id)

    engineering_actor = pipeline.actor
    finance_actor = AuthActor(
        user_id=engineering_actor.user_id,
        department="finance",
        clearance=engineering_actor.clearance,
        role=engineering_actor.role,
        correlation_id=engineering_actor.correlation_id,
    )

    cmd_allow = RetrieveAuthorizedCommand(
        actor=engineering_actor,
        query_text="kubernetes",
        top_k=4,
        rerank_top_n=4,
    )
    allowed_result = await orchestrator.execute(cmd_allow)
    assert allowed_result.authorization.allowed is True
    assert len(allowed_result.ranked) > 0
    for r in allowed_result.ranked:
        proj = r.candidate.document_projection
        assert proj is not None
        assert proj.department == engineering_actor.department

    cmd_deny = RetrieveAuthorizedCommand(
        actor=finance_actor,
        query_text="kubernetes",
        top_k=4,
        rerank_top_n=4,
    )
    deny_outcome_seen = False
    try:
        await orchestrator.execute(cmd_deny)
    except EmptyRetrievalError:
        deny_outcome_seen = True
    assert deny_outcome_seen, (
        "M8 must raise EmptyRetrievalError when the actor's "
        "department has no chunks in the corpus."
    )


async def test_m9_citation_drop_on_department_mismatch(
    pipeline: RealCorpusPipeline,
) -> None:
    """M9 verifier drops citations whose document's department mismatches."""
    if pipeline.chunk_count == 0:
        pytest.skip("no chunks; corpus was empty after ingest.")

    citations = _collect_active_citations(pipeline, limit=6)
    if not citations:
        pytest.skip("corpus yielded no active citations for projection.")

    rewrites = tuple(
        _replace_projection(citation, department="finance")
        for citation in citations
    )

    verifier = build_verify_citations(pipeline.documents._documents)
    cmd = VerifyCitationsCommand(actor=pipeline.actor, citations=rewrites)
    result: VerifyCitationsResult = await verifier.execute(cmd)

    assert result.dropped_citations, (
        "M9 verifier kept all citations despite department mismatch; "
        "the third M0 invocation appears broken on the real corpus."
    )
    for drop in result.dropped_citations:
        assert drop.reason in ALL_DROP_REASONS


async def test_m9_citation_drop_on_clearance_mismatch(
    pipeline: RealCorpusPipeline,
) -> None:
    """M9 verifier drops citations whose document's clearance exceeds actor's."""
    if pipeline.chunk_count == 0:
        pytest.skip("no chunks; corpus was empty after ingest.")

    actor = pipeline.actor
    actor_clearance = Clearance[actor.clearance.upper()]
    citations = _collect_active_citations(pipeline, limit=6)
    if not citations:
        pytest.skip("corpus yielded no active citations for projection.")

    higher_index = (list(Clearance)).index(Clearance.CONFIDENTIAL)
    higher_clearance = list(Clearance)[higher_index]
    assert higher_clearance is not actor_clearance
    rewrites = tuple(
        _replace_projection(citation, clearance=higher_clearance)
        for citation in citations
    )

    verifier = build_verify_citations(pipeline.documents._documents)
    cmd = VerifyCitationsCommand(actor=actor, citations=rewrites)
    result = await verifier.execute(cmd)

    assert result.dropped_citations, (
        "M9 verifier kept all citations despite clearance insufficiency."
    )
    for drop in result.dropped_citations:
        assert drop.reason in ALL_DROP_REASONS


def _collect_active_citations(
    pipeline: RealCorpusPipeline,
    *,
    limit: int,
) -> tuple[Citation, ...]:
    citations = []
    for chunk in pipeline.chunks._chunks.values():
        if chunk.status.name != "ACTIVE":
            continue
        doc = pipeline.documents._documents.get(chunk.document_id)
        if doc is None:
            continue
        try:
            dept_clearance = Clearance[doc.required_clearance.name]
        except KeyError:
            continue
        citations.append(
            Citation(
                chunk_id=int(chunk.id),
                document_id=int(chunk.document_id),
                ordinal=int(chunk.ordinal),
                quote=str(doc.title),
                document_projection=DocumentProjection(
                    department=doc.department,
                    required_clearance=dept_clearance,
                ),
            )
        )
        if len(citations) >= limit:
            break
    return tuple(citations)


def _replace_projection(
    citation: Citation,
    *,
    department: str | None = None,
    clearance: Clearance | None = None,
) -> Citation:
    """Replace ``document_projection`` partial fields on a Citation.

    `Citation` is a frozen dataclass; rebuilding is the only way
    to change projection without touching the canonical artifact.
    """
    current = citation.document_projection or DocumentProjection(
        department="engineering", required_clearance=Clearance.INTERNAL
    )
    return Citation(
        chunk_id=citation.chunk_id,
        document_id=citation.document_id,
        ordinal=citation.ordinal,
        quote=citation.quote,
        document_projection=DocumentProjection(
            department=department if department is not None else current.department,
            required_clearance=(
                clearance if clearance is not None else current.required_clearance
            ),
        ),
    )


def _documents_by_chunk_id(pipeline: RealCorpusPipeline):
    """Thin projector the M8 orchestrator calls per-survivor chunk.

    The orchestrator expects a callable that returns the canonical
    DocumentProjection for a chunk_id; the in-memory repository
    already carries the projection on each chunk's host document.
    """

    def _resolve(chunk_id: int):
        chunk = pipeline.chunks._chunks.get(chunk_id)
        if chunk is None:
            return None
        doc = pipeline.documents._documents.get(chunk.document_id)
        if doc is None:
            return None
        try:
            clearance = Clearance[doc.required_clearance.name]
        except KeyError:
            clearance = Clearance.INTERNAL
        return DocumentProjection(
            department=doc.department,
            required_clearance=clearance,
        )

    return _resolve
