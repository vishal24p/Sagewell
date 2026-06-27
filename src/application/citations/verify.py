"""M9 — Verify Citations use case.

The use case applies the M0 access-decision pure function
to a list of generated citations. Citations whose documents
evaluate deny are dropped; survivors are returned with the
literal `(allowed, reason)` pair so the workflow boundary
can audit the drop or the survival.

This is the third M0 invocation per `AGENTS.md`
Architectural Guardrails:

  1. M8 pre-retrieval projection.
  2. M8 post-rerank drop.
  3. M9 citation verification.

The use case is pure: it does not write audit rows; it does
not call the database directly. The workflow layer is
responsible for persisting the audit row through M4's
`RecordAuditEvent` -- the use case surfaces the typed
outcome so the workflow can attribute each drop to its
reason.

Three guarantees:

  - The decision function is invoked exactly once per
    citation. No caching; no pre-computed batches.
  - Citations whose `document_projection` is set (an M8
    in-memory / Postgres adapter that pre-projected) are
    verified without a documents-port round-trip.
  - Citations whose `document_projection` is NOT set are
    resolved via the `documents_by_id` callable. When the
    document cannot be resolved (the callable returns
    `None`), the citation FAILS CLOSED. The verifier uses
    `Reason.MISSING_DOCUMENT_DEPARTMENT` /
    `MISSING_DOCUMENT_CLEARANCE` since the missing-input
    branch is fail-closed by the M0 pure function.

The outputs:

  - `VerifyCitationsCommand`: typed command.
  - `VerifyCitationsResult`: typed result carrying:
      `allowed_citations` (passed) + `dropped_citations`
      (denied with reason).
  - typed errors:
      - `CitationVerificationError` -- domain anchor.
      - `EmptyCitationsError` -- empty input failure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from src.application.auth.dto import AuthActor
from src.domain.access.access_decision import (
    AccessResult,
    Reason as DecisionReason,
    decide,
)
from src.domain.ports.citations import Citation
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentProjection
from src.domain.ports.users import UserProjection


__all__ = [
    "VerifyCitations",
    "VerifyCitationsCommand",
    "VerifyCitationsResult",
    "DroppedCitation",
    "CitationVerificationError",
    "EmptyCitationsError",
    "CitationDecisionUnavailableError",
]


@dataclass(frozen=True)
class DroppedCitation:
    """A citation whose document evaluated deny.

    Carries the failure reason so the workflow boundary
    can record an `audit_logs` row with the typed reason
    code (one of `MISSING_DOCUMENT_DEPARTMENT`,
    `MISSING_DOCUMENT_CLEARANCE`, `department_mismatch`,
    `clearance_insufficient`).
    """

    citation: Citation
    reason: str


@dataclass(frozen=True)
class VerifyCitationsCommand:
    """Typed command.

    The actor's clearance/translation lives here. The
    `documents_by_id` callable resolves `DocumentProjection`
    for any citation that did not pre-project.
    """

    actor: AuthActor
    citations: Sequence[Citation]


@dataclass(frozen=True)
class VerifyCitationsResult:
    """Typed result.

    `allowed_citations` is the survivor list in input
    order. `dropped_citations` is symmetric on the
    drop side. `total` = `len(citations)` from the
    command (input cardinality).
    """

    allowed_citations: tuple[Citation, ...]
    dropped_citations: tuple[DroppedCitation, ...]
    total: int


class CitationVerificationError(Exception):
    code: str = "citation_verification_failure"


class EmptyCitationsError(CitationVerificationError):
    code: str = "empty_citations"


class CitationDecisionUnavailableError(CitationVerificationError):
    code: str = "citation_decision_unavailable"


def _clearance_from_str(value: str) -> Optional[Clearance]:
    """Translate JWT-supplied clearance to the V1 enum.

    `None` is returned for blank input so the M0 pure
    function's fail-closed rule surfaces a typed
    missing-user-clearance reason rather than crashing.
    Unrecognized non-blank strings raise
    `CitationDecisionUnavailableError`; the workflow
    boundary translates that into a non-200 response.
    """
    if value is None or not value.strip():
        return None
    upper = value.strip().upper()
    try:
        return Clearance[upper]
    except KeyError as exc:
        raise CitationDecisionUnavailableError(
            f"actor clearance {value!r} is not a V1 ladder step."
        ) from exc


def _resolve_document_projection(
    citation: Citation,
    documents_by_id,
) -> Optional[DocumentProjection]:
    """Return the document's authorization projection.

    Prefers the citation's pre-projected value when set.
    Falls back to the documents-port callable when not.
    Returns `None` when neither side has the projection.
    """
    if citation.document_projection is not None:
        return citation.document_projection
    document = documents_by_id(citation.document_id)
    if document is None:
        return None
    return document.as_authorization_projection()


class VerifyCitations:
    """The M9 citation-verification use case.

    Constructor dependencies:

      `documents_by_id`: a callable / repository method
        that returns a `Document` row for a document_id,
        or `None` when the document is missing. M9 ships
        a thin callback against the M2 ports; the
        production call site is
        `documents.find_active_by_ids()`
        followed by `as_authorization_projection()`.
    """

    def __init__(self, *, documents_by_id) -> None:
        self._documents_by_id = documents_by_id

    async def execute(self, command: VerifyCitationsCommand) -> VerifyCitationsResult:
        citations = list(command.citations or ())
        if not citations:
            raise EmptyCitationsError(
                "VerifyCitations.execute requires at least one citation."
            )

        actor_clearance_value = _clearance_from_str(command.actor.clearance)
        if actor_clearance_value is None:
            user = UserProjection(
                department=command.actor.department,
                clearance=None,
            )
        else:
            user = UserProjection(
                department=command.actor.department,
                clearance=actor_clearance_value,
            )

        allowed: list[Citation] = []
        dropped: list[DroppedCitation] = []
        for citation in citations:
            doc_projection = _resolve_document_projection(
                citation, self._documents_by_id
            )
            if doc_projection is None:
                projection_for_decide = DocumentProjection(
                    department=None,
                    required_clearance=None,
                )
            else:
                projection_for_decide = doc_projection
            decision: AccessResult = decide(user, projection_for_decide)
            ok, reason = decision
            if ok:
                allowed.append(citation)
            else:
                dropped.append(DroppedCitation(citation=citation, reason=reason))

        return VerifyCitationsResult(
            allowed_citations=tuple(allowed),
            dropped_citations=tuple(dropped),
            total=len(citations),
        )
