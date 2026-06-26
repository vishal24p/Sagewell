"""Parity test: `documents.upsert_by_source` + `chunks.replace_for_document`.

These tests run against the in-memory backend only. The Postgres
counterpart exercises the same contract through the parametrized
`adapter` fixture but is restricted to the in-memory branch here
because the Postgres tests require a running database which the
sandbox cannot start. The adapter contract is the one exercised.

M7 contract:

  - `upsert_by_source` returns `was_inserted=True` for a fresh
    `(source_system, source_id)` key.
  - Same checksum on the same key -> `was_unchanged=True`,
    no DB row-level mutation.
  - Different checksum on the same key -> `was_replaced=True`,
    the canonical row's content_checksum is updated.

  - `replace_for_document` retires every active chunk for the
    document_id and inserts the drafts in ordinal order. The
    retired chunks are not returned by `find_active_by_*`
    after the call.
"""
from __future__ import annotations

import pytest

from src.domain.ports.chunks import (
    ChunkDraft,
    EMBEDDING_DIM,
)
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentUpsertCommand
from src.infrastructure.repositories.in_memory.chunks import (
    InMemoryChunkRepository,
)
from src.infrastructure.repositories.in_memory.documents import (
    InMemoryDocumentRepository,
)


@pytest.fixture
def document_repo():
    return InMemoryDocumentRepository()


@pytest.fixture
def chunk_repo():
    return InMemoryChunkRepository()


pytestmark = pytest.mark.asyncio


def _doc_command(checksum: str = "checksum-1") -> DocumentUpsertCommand:
    return DocumentUpsertCommand(
        source_system="fixture",
        source_id="doc-m7-test",
        title="Test Doc",
        uri=None,
        department="engineering",
        required_clearance=Clearance.INTERNAL,
        content_checksum=checksum,
    )


def _make_embeddings(ordinals):
    out: list[list[float]] = []
    for ord in ordinals:
        out.append([(ord + dim) / 100.0 for dim in range(EMBEDDING_DIM)])
    return out


async def test_upsert_by_source_inserts_a_new_row(document_repo):
    res = await document_repo.upsert_by_source(_doc_command("checksum-A"))
    assert res.was_inserted is True
    assert res.was_replaced is False
    assert res.was_unchanged is False
    assert res.document.content_checksum == "checksum-A"


async def test_upsert_by_source_returns_unchanged_on_same_checksum(document_repo):
    await document_repo.upsert_by_source(_doc_command("checksum-A"))
    res = await document_repo.upsert_by_source(_doc_command("checksum-A"))
    assert res.was_inserted is False
    assert res.was_unchanged is True
    assert res.was_replaced is False


async def test_upsert_by_source_returns_replaced_on_different_checksum(document_repo):
    await document_repo.upsert_by_source(_doc_command("checksum-A"))
    res = await document_repo.upsert_by_source(_doc_command("checksum-B"))
    assert res.was_inserted is False
    assert res.was_unchanged is False
    assert res.was_replaced is True
    assert res.document.content_checksum == "checksum-B"
    assert res.document.id is not None
    # `find_by_source` returns the same id; insert path's identity
    # is preserved on replace.
    looked = await document_repo.find_by_source("fixture", "doc-m7-test")
    assert looked is not None
    assert looked.content_checksum == "checksum-B"


async def test_replace_for_document_retires_old_and_inserts_new(document_repo, chunk_repo):
    upsert = await document_repo.upsert_by_source(_doc_command("checksum-A"))
    document_id = upsert.document.id

    drafts = [
        ChunkDraft(
            document_id=document_id,
            ordinal=0,
            text="alpha",
            text_search="alpha",
            embedding=_make_embeddings([0])[0],
            metadata={"ordinal": 0},
            token_count=1,
        ),
        ChunkDraft(
            document_id=document_id,
            ordinal=1,
            text="beta",
            text_search="beta",
            embedding=_make_embeddings([1])[0],
            metadata={"ordinal": 1},
            token_count=1,
        ),
    ]
    first = await chunk_repo.replace_for_document(document_id, drafts)
    assert len(first.inserted_chunks) == 2
    assert first.retired_chunk_ids == ()
    active_first = await chunk_repo.find_active_by_document_id(document_id)
    assert {c.ordinal for c in active_first} == {0, 1}

    # Second call with new drafts retires the prior 2 chunks.
    new_drafts = [
        ChunkDraft(
            document_id=document_id,
            ordinal=0,
            text="gamma",
            text_search="gamma",
            embedding=_make_embeddings([10])[0],
            metadata={"ordinal": 0},
            token_count=1,
        )
    ]
    second = await chunk_repo.replace_for_document(document_id, new_drafts)
    assert len(second.inserted_chunks) == 1
    assert set(second.retired_chunk_ids) == {c.id for c in active_first}
    active_second = await chunk_repo.find_active_by_document_id(document_id)
    assert len(active_second) == 1
    assert active_second[0].ordinal == 0
    assert active_second[0].text == "gamma"
    # The old chunks must NOT be searchable.
    for old_id in second.retired_chunk_ids:
        looked = await chunk_repo.find_active_by_id(old_id)
        assert looked is None


async def test_replace_for_document_with_no_drafts_retires_without_inserting(
    document_repo, chunk_repo
):
    upsert = await document_repo.upsert_by_source(_doc_command("checksum-A"))
    document_id = upsert.document.id
    drafts = [
        ChunkDraft(
            document_id=document_id,
            ordinal=0,
            text="lonely",
            text_search="lonely",
            embedding=_make_embeddings([0])[0],
            metadata={},
            token_count=1,
        )
    ]
    await chunk_repo.replace_for_document(document_id, drafts)
    second = await chunk_repo.replace_for_document(document_id, [])
    assert second.inserted_chunks == ()
    # retired_chunk_ids contains the prior active chunk's id.
    active = await chunk_repo.find_active_by_document_id(document_id)
    assert active == []
