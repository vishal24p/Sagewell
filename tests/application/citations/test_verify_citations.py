"""M9 VerifyCitations use case tests.

Six tests:

1. happy_path_drops_unauthorized -- the citation whose
   document evaluates deny is dropped; the rest survive.
2. fail_closed_on_missing_document -- when the documents
   port returns None, the missing-document branch of
   the pure function deny-fails the citation.
3. missing_user_clearance_short_circuits -- a blank
   actor clearance cascades into a typed
   missing_user_clearance drop on every citation.
4. pre_projected_document_skips_lookup -- a citation
   whose document_projection is set is verified without
   consulting the documents port.
5. empty_citations_raises_typed_error -- the
   `EmptyCitationsError` carries `code: empty_citations`.
6. unrecognized_clearance_raises_decision_unavailable --
   the typed-error envelope translates to a 503-class
   failure when an actor carries a non-V1 step.
"""
from __future__ import annotations

import pytest

from src.application.auth.dto import AuthActor
from src.application.citations.verify import (
    CitationDecisionUnavailableError,
    EmptyCitationsError,
    VerifyCitations,
    VerifyCitationsCommand,
)
from src.domain.ports.citations import Citation
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import Document, DocumentProjection, DocumentStatus


class _DictDocuments:
    def __init__(self, by_id):
        self.by_id = by_id
        self.calls = []

    def __call__(self, document_id):
        self.calls.append(document_id)
        return self.by_id.get(document_id)


pytestmark = pytest.mark.asyncio


def _projection(department: str, clearance: Clearance):
    return DocumentProjection(
        department=department,
        required_clearance=clearance,
    )


def _doc(document_id: int, department: str, clearance: Clearance):
    import datetime
    return Document(
        id=document_id,
        source_system="test",
        source_id=f"src-{document_id}",
        title="t",
        uri=None,
        status=DocumentStatus.ACTIVE,
        department=department,
        required_clearance=clearance,
        content_checksum="a" * 64,
        created_at=datetime.datetime(2026, 1, 1),
        updated_at=datetime.datetime(2026, 1, 1),
    )


def _actor(clearance: str = "internal"):
    return AuthActor(
        user_id="u-m9",
        department="engineering",
        clearance=clearance,
        role="contributor",
        correlation_id="corr-m9",
    )


async def test_happy_path_drops_unauthorized():
    citations = (
        Citation(
            chunk_id=1,
            document_id=100,
            ordinal=0,
            quote="ok quote 1",
            document_projection=_projection(
                "engineering", Clearance.INTERNAL
            ),
        ),
        Citation(
            chunk_id=2,
            document_id=200,
            ordinal=0,
            quote="bad quote",
            document_projection=_projection(
                "legal", Clearance.CONFIDENTIAL
            ),
        ),
        Citation(
            chunk_id=3,
            document_id=300,
            ordinal=0,
            quote="ok quote 3",
            document_projection=_projection(
                "engineering", Clearance.INTERNAL
            ),
        ),
    )
    cmd = VerifyCitationsCommand(actor=_actor(), citations=citations)
    use_case = VerifyCitations(documents_by_id=_DictDocuments({}))
    result = await use_case.execute(cmd)
    assert result.total == 3
    assert len(result.allowed_citations) == 2
    assert {c.chunk_id for c in result.allowed_citations} == {1, 3}
    assert len(result.dropped_citations) == 1
    drop = result.dropped_citations[0]
    assert drop.citation.chunk_id == 2
    assert drop.reason == "department_mismatch"


async def test_fail_closed_on_missing_document():
    citations = (
        Citation(
            chunk_id=4,
            document_id=999,
            ordinal=0,
            quote="orphan quote",
        ),
    )
    cmd = VerifyCitationsCommand(actor=_actor(), citations=citations)
    use_case = VerifyCitations(documents_by_id=_DictDocuments({}))
    result = await use_case.execute(cmd)
    assert result.total == 1
    assert result.allowed_citations == ()
    assert len(result.dropped_citations) == 1
    drop = result.dropped_citations[0]
    assert drop.reason in {
        "missing_document_department",
        "missing_document_clearance",
    }


async def test_missing_user_clearance_short_circuits():
    citations = (
        Citation(
            chunk_id=5,
            document_id=100,
            ordinal=0,
            quote="q",
            document_projection=_projection(
                "engineering", Clearance.INTERNAL
            ),
        ),
    )
    cmd = VerifyCitationsCommand(actor=_actor(clearance=""), citations=citations)
    use_case = VerifyCitations(documents_by_id=_DictDocuments({}))
    result = await use_case.execute(cmd)
    assert result.allowed_citations == ()
    assert len(result.dropped_citations) == 1
    drop = result.dropped_citations[0]
    assert drop.reason == "missing_user_clearance"


async def test_pre_projected_document_skips_lookup():
    citations = (
        Citation(
            chunk_id=6,
            document_id=100,
            ordinal=0,
            quote="pre-projected quote",
            document_projection=_projection(
                "engineering", Clearance.INTERNAL
            ),
        ),
    )
    port = _DictDocuments({})
    use_case = VerifyCitations(documents_by_id=port)
    result = await use_case.execute(
        VerifyCitationsCommand(actor=_actor(), citations=citations)
    )
    assert len(result.allowed_citations) == 1
    assert port.calls == []


async def test_empty_citations_raises_typed_error():
    use_case = VerifyCitations(documents_by_id=_DictDocuments({}))
    with pytest.raises(EmptyCitationsError):
        await use_case.execute(
            VerifyCitationsCommand(actor=_actor(), citations=())
        )


async def test_unrecognized_clearance_raises_decision_unavailable():
    citations = (
        Citation(
            chunk_id=7,
            document_id=100,
            ordinal=0,
            quote="q",
            document_projection=_projection(
                "engineering", Clearance.INTERNAL
            ),
        ),
    )
    cmd = VerifyCitationsCommand(
        actor=_actor(clearance="super-nuclear"), citations=citations
    )
    use_case = VerifyCitations(documents_by_id=_DictDocuments({}))
    with pytest.raises(CitationDecisionUnavailableError):
        await use_case.execute(cmd)
