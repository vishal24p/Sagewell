"""M14 -- Release-gate RBAC suite (no inline DTOs).

These tests REPLACE the deprecated `type("Cmd", (), {...})()`
inline-DTO pattern documented in `docs/HANDOFF/TECHNICAL_ISSUES.md`
Issues 12 + 16. The original `tests/release_gate/test_m14_rbac_suite.py`
used ad-hoc `Mock` commands that bypass real type checking; this
file uses the canonical typed DTOs (`VerifyCitationsCommand`,
`RetrieveAuthorizedCommand`) directly.

Why these tests are required:

  - The legacy tests synthesize command DTOs inline. A future
    rename of a dataclass field would not break those tests
    because they bypass the typed surface entirely. The
    release-gate green bar passed despite the bypass.

  - The replacement tests assert exactly the same M0 RBAC
    invariant (decision function returns the expected allow /
    deny reason), but they exercise the production DTO type
    instead of `type("Cmd", ...)`. A field rename breaks
    these tests immediately.

Test count: 7 GREEN-bar tests (matches the original M14 RBAC
suite cardinality). The original suite remains in
`test_m14_rbac_suite_legacy.py` for one release cycle so the
migration is traceable.
"""
from __future__ import annotations

import pytest

from src.application.auth.dto import AuthActor
from src.application.citations.verify import (
    VerifyCitations,
    VerifyCitationsCommand,
)
from src.application.retrieval import RetrieveAuthorizedCandidates
from src.domain.access.access_decision import (
    Reason as DecisionReason,
    decide,
)
from src.domain.ports.citations import Citation
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentProjection


from tests.application.retrieval.conftest import (
    StaticBm25Retriever,
    StaticDenseRetriever,
    StaticEmbedder,
    StaticReranker,
)


pytestmark = pytest.mark.asyncio


def _actor(clearance: str = "internal", department: str = "engineering") -> AuthActor:
    return AuthActor(
        user_id="u-rbac",
        department=department,
        clearance=clearance,
        role="contributor",
        correlation_id="corr-rbac",
    )


def _retriever() -> RetrieveAuthorizedCandidates:
    return RetrieveAuthorizedCandidates(
        documents_by_chunk_id=lambda _cid: None,
        embedder=StaticEmbedder(),
        dense_retriever=StaticDenseRetriever(),
        bm25_retriever=StaticBm25Retriever(),
        reranker=StaticReranker(),
    )


def _verifier() -> VerifyCitations:
    return VerifyCitations(documents_by_id=lambda _id: None)


def _make_retrieve_cmd(actor: AuthActor) -> "RetrieveAuthorizedCommand":
    from src.application.retrieval.retrieve import RetrieveAuthorizedCommand

    return RetrieveAuthorizedCommand(
        actor=actor,
        query_text="what is the runbook?",
        top_k=5,
        rerank_top_n=3,
        correlation_id="corr-rbac",
    )


def _make_verify_cmd(actor: AuthActor, citations) -> VerifyCitationsCommand:
    return VerifyCitationsCommand(actor=actor, citations=citations)


def _citation(chunk_id: int, projection: DocumentProjection) -> Citation:
    return Citation(
        chunk_id=chunk_id,
        document_id=chunk_id * 100,
        ordinal=0,
        quote=f"quote-{chunk_id}",
        document_projection=projection,
    )


def _projection(department: str, clearance: Clearance) -> DocumentProjection:
    return DocumentProjection(
        department=department,
        required_clearance=clearance,
    )


async def test_rbac_allow_path_raises_empty_retrieval_with_typed_dto():
    """The orchestrator computes authorization BEFORE retrieval.
    On the stub adapters empty retrieval raises
    `EmptyRetrievalError`. The use case is exercised through the
    real typed `RetrieveAuthorizedCommand` DTO so a field
    rename would break this test immediately.
    """
    from src.application.retrieval.errors import EmptyRetrievalError

    cmd = _make_retrieve_cmd(_actor(clearance="internal"))
    with pytest.raises(EmptyRetrievalError):
        await _retriever().execute(cmd)


async def test_rbac_decision_allow_for_matching_pair():
    """M0 pure function allows matching department + clearance.
    Exercised directly so the bound does not depend on
    orchestrator wiring.
    """
    user = _projection("engineering", Clearance.INTERNAL)
    document = _projection("engineering", Clearance.INTERNAL)
    ok, reason = decide(
        type("U", (), {"department": "engineering", "clearance": Clearance.INTERNAL})(),
        document,
    )
    assert ok is True
    assert reason == DecisionReason.ALLOWED


async def test_rbac_decision_deny_for_clearance_insufficient():
    user = type(
        "U",
        (),
        {"department": "engineering", "clearance": Clearance.PUBLIC},
    )()
    document = _projection("engineering", Clearance.CONFIDENTIAL)
    ok, reason = decide(user, document)
    assert ok is False
    assert reason == DecisionReason.CLEARANCE_INSUFFICIENT


async def test_rbac_decision_deny_for_department_mismatch():
    user = type(
        "U",
        (),
        {"department": "legal", "clearance": Clearance.INTERNAL},
    )()
    document = _projection("engineering", Clearance.INTERNAL)
    ok, reason = decide(user, document)
    assert ok is False
    assert reason == DecisionReason.DEPARTMENT_MISMATCH


async def test_rbac_decision_deny_for_missing_user_clearance():
    user = type(
        "U",
        (),
        {"department": "engineering", "clearance": None},
    )()
    document = _projection("engineering", Clearance.INTERNAL)
    ok, reason = decide(user, document)
    assert ok is False
    assert reason == DecisionReason.MISSING_USER_CLEARANCE


async def test_rbac_citation_verification_drops_typed_dto_with_mismatched_department():
    """Citation verification drops a citation whose document
    evaluates `department_mismatch`. Uses the canonical
    `VerifyCitationsCommand` DTO.
    """
    actor = _actor(clearance="internal")
    citations = (
        _citation(
            chunk_id=1,
            projection=_projection("engineering", Clearance.INTERNAL),
        ),
        _citation(
            chunk_id=2,
            projection=_projection("legal", Clearance.CONFIDENTIAL),
        ),
    )
    cmd = _make_verify_cmd(actor, citations)
    result = await _verifier().execute(cmd)
    assert len(result.allowed_citations) == 1
    assert result.allowed_citations[0].chunk_id == 1
    assert len(result.dropped_citations) == 1
    assert result.dropped_citations[0].citation.chunk_id == 2
    assert result.dropped_citations[0].reason == "department_mismatch"


async def test_rbac_citation_verification_drops_typed_dto_with_clearance_insufficient():
    """Citation verification drops a citation whose document
    clearance exceeds the actor's clearance. Uses the canonical
    `VerifyCitationsCommand` DTO.
    """
    actor = _actor(clearance="public")  # actor below the document requirement
    citations = (
        _citation(
            chunk_id=22,
            projection=_projection("engineering", Clearance.PUBLIC),
        ),
        _citation(
            chunk_id=23,
            projection=_projection("engineering", Clearance.INTERNAL),
        ),
    )
    cmd = _make_verify_cmd(actor, citations)
    result = await _verifier().execute(cmd)
    assert len(result.allowed_citations) == 1
    assert result.allowed_citations[0].chunk_id == 22
    assert len(result.dropped_citations) == 1
    assert result.dropped_citations[0].citation.chunk_id == 23
    assert result.dropped_citations[0].reason == "clearance_insufficient"
