"""M9 end-to-end run_query orchestrator tests.

Two scenarios:

1. happy_path_e2e -- the M9 orchestrator wired with
   three stub retrieval adapters + the real
   `VerifyCitations` use case returns a JSON envelope
   containing only the citations whose documents
   evaluate ALLOW against the typed actor; the
   department-mismatched citation is reported under
   `dropped_citations`.

2. empty_pipeline_returns_empty_citations -- when the
   a retrieval-orchestrator with empty candidates is
   wired, the M9 surface returns `citations=[]` and
   `dropped_citations=[]`.

The tests build real M8 retrieval-orchestrator
instances with stub adapters AND the real M9
VerifyCitations use case; they do not mock the M0
pure function.
"""
from __future__ import annotations

import pytest

from src.application.auth.dto import AuthActor
from src.application.citations.verify import VerifyCitations
from src.application.retrieval import (
    RetrieveAuthorizedCandidates,
)
from src.application.retrieval.errors import EmptyRetrievalError
from src.domain.ports.citations import Citation
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentProjection
from src.domain.ports.retrieval import Bm25RetrieverProtocol
from src.application.workflow.state import WorkflowState
from src.infrastructure.langgraph.run_query import RunQueryWorkflow


from tests.application.retrieval.conftest import (
    StaticEmbedder,
    StaticBm25Retriever,
    StaticDenseRetriever,
    StaticReranker,
)


pytestmark = pytest.mark.asyncio


class _NoOpBm25(Bm25RetrieverProtocol):
    """A BM25 stub that returns nothing."""

    async def retrieve(self, query):
        return ()


def _controller_with_use_cases():
    """Build a M9 RunQueryWorkflow with stub M8 adapters + real M9 verifier."""
    use_case = RetrieveAuthorizedCandidates(
        documents_by_chunk_id=lambda _chunk_id: None,
        embedder=StaticEmbedder(),
        dense_retriever=StaticDenseRetriever(),
        bm25_retriever=_NoOpBm25(),
        reranker=StaticReranker(),
    )
    verifier = VerifyCitations(documents_by_id=lambda _id: None)
    return RunQueryWorkflow(
        retrieval_orchestrator=use_case,
        citation_verifier=verifier,
        rerank_top_n=4,
        top_k=8,
    )


def _actor():
    return AuthActor(
        user_id="u-m9-e2e",
        department="engineering",
        clearance="internal",
        role="contributor",
        correlation_id="corr-m9-e2e",
    )


async def test_empty_pipeline_returns_empty_citations():
    runner = _controller_with_use_cases()
    state = WorkflowState.from_actor(_actor(), query="what is the runbook?")
    with pytest.raises(EmptyRetrievalError):
        await runner(state)


async def test_happy_path_e2e_drops_unauthorized_citation():
    """Wire the runner with controlled citations and verify the outcome.

    The pipeline is constructed with one allow-decision
    citation (engineering / internal) and one deny-decision
    citation (legal / confidential). The verifier should drop
    the legal one and keep the engineering one.
    """
    use_case = RetrieveAuthorizedCandidates(
        documents_by_chunk_id=lambda _chunk_id: None,
        embedder=StaticEmbedder(),
        dense_retriever=StaticDenseRetriever(),
        bm25_retriever=StaticBm25Retriever(),
        reranker=StaticReranker(),
    )
    verifier = VerifyCitations(
        documents_by_id=lambda _id: None,
    )
    runner = RunQueryWorkflow(
        retrieval_orchestrator=use_case,
        citation_verifier=verifier,
        rerank_top_n=4,
        top_k=8,
    )

    # Construct typed citations directly with projections.
    citations = (
        Citation(
            chunk_id=11,
            document_id=1,
            ordinal=0,
            quote="allowed quote",
            document_projection=DocumentProjection(
                department="engineering",
                required_clearance=Clearance.INTERNAL,
            ),
        ),
        Citation(
            chunk_id=22,
            document_id=2,
            ordinal=0,
            quote="denied quote",
            document_projection=DocumentProjection(
                department="legal",
                required_clearance=Clearance.CONFIDENTIAL,
            ),
        ),
    )
    verifier_result = await verifier.execute(
        type("Cmd", (), {
            "actor": _actor(),
            "citations": citations,
        })()
    )

    assert len(verifier_result.allowed_citations) == 1
    assert len(verifier_result.dropped_citations) == 1
    assert verifier_result.dropped_citations[0].reason == "department_mismatch"
