"""V1 Citation port (M9).

A `Citation` is the typed contract for a chunk-attached
quote in a generated answer. The M9 workflow drops every
citation whose document fails the M0 access-decision
pure function (the third invocation per
`AGENTS.md` Architectural Guardrails).

Citation shape:

  - `chunk_id`: the canonical row from `chunks.id`.
  - `document_id`: the canonical row from
    `documents.id`. The citation uses the document-id so
    the verifier looks up the authorization projection in
    one read.
  - `ordinal`: the chunk's position within the document.
  - `quote`: the chunk's text excerpt. Stored verbatim in
    audit rows only when `quote_pii_safe` confirms no PII
    is present; redacted otherwise. M9 carries the quote
    end-to-end; the redactor lands at a future milestone.
  - `document_projection`: optional `DocumentProjection`
    carried by skills that already projected the
    document's authorization columns. When `None`, the
    citation-verification step resolves the projection
    from the `documents_by_id` repository. When the
    projection is `None` after resolution, the citation
    fails-closed: the verifier treats unavailable
    authorization info as a deny.

The verifier does NOT re-implement the access-decision
rule. The M0 pure function (`decide(user, document)`) is
the single source of truth, invoked at three boundaries:

  1. Pre-retrieval projection (M8) -- sets the SQL filter.
  2. Post-rerank drop (M8) -- drops candidates whose
     documents evaluate deny.
  3. Citation verification (M9) -- drops citations whose
     documents evaluate deny.

The `Citation` port's `document_projection` field exists
so adapters (in-memory first, pgvector / pg_search later)
can populate the projection synchronously. The verifier
short-circuits on a populated projection; only when it is
absent does the verifier consult the documents port.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .documents import DocumentProjection


@dataclass(frozen=True)
class Citation:
    """The typed contract for a chunk-attached quote in an answer.

    `chunk_id`, `document_id`, `ordinal` are canonical row ids.
    `quote` is the verbatim chunk excerpt carried end-to-end (a
    future milestone introduces the PII redactor). The
    `document_projection` field is the M0-pure-function input;
    when populated by an adapter, the citation verifier reads
    it directly. When `None`, the verifier resolves from the
    documents port (see `CitationVerifyResult.citations`).
    """

    chunk_id: int
    document_id: int
    ordinal: int
    quote: str
    document_projection: Optional[DocumentProjection] = None


__all__ = ["Citation"]
