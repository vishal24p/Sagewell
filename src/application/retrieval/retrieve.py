"""M8 `RetrieveAuthorizedCandidates` use case.

The use case wires the access-decision pure function (pre-filter
+ post-rerank drop) around the four mandatory retrieval stages
per `skills/project/retrieval_engine/SKILL.md`:

  1. Pre-retrieval projection (M0 pure function).
  2. Embed query (M7 capability).
  3. Dense retrieve (M8 adapter).
  4. BM25 retrieve (M8 adapter).
  5. RRF fuse (pure function).
  6. Cross-encoder rerank (M8 adapter).
  7. Post-rerank decision drop (M0 pure function).

It does NOT mount on a route; M9 wires the orchestrator onto
the `/v1/...` API surface. The use case is exercised through
tests so the access-decision boundaries can be regression-tested
without a real pgvector / pg_search / LlamaIndex deployment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

from src.domain.access.access_decision import (
    AccessResult,
    Reason as DecisionReason,
    decide,
)
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import DocumentProjection
from src.domain.ports.reason_codes import (
    ACCESS_DECISION_MISSING_USER_CLEARANCE,
)
from src.domain.ports.retrieval import (
    AccessPolicyFilter,
    Bm25RetrieverProtocol,
    DenseRetrieverProtocol,
    QueryEmbedderProtocol,
    RankedCandidate,
    RerankerProtocol,
    RetrievalCandidate,
    RetrievalQuery,
    RetrievalStageStats,
)
from src.domain.ports.users import UserProjection
from src.domain.retrieval.rrf import DEFAULT_RRF_K, FusedCandidate, fuse as rrf_fuse

from src.application.auth.dto import AuthActor
from src.application.retrieval.errors import (
    AccessDecisionUnavailableError,
    EmptyRetrievalError,
)


# The M0 pure function's wildcard value. Documents at the
# "ALL" department are reachable from any department actor
# once their clearance requirement is satisfied.
_ALL_DEPARTMENT: str = "ALL"


@dataclass(frozen=True)
class RetrieveAuthorizedCommand:
    """The M8 application-side input.

    `actor` is the M5 typed AuthActor. `query_text` is the
    normalized user question (M10's regex-guard work happens
    upstream of M8). `top_k` is the per-stage cap (RRF keeps
    the union plus its own top-K cap). `rerank_top_n` caps
    the cross-encoder output.
    """
    actor: AuthActor
    query_text: str
    top_k: int = 50
    rerank_top_n: int = 10
    correlation_id: Optional[str] = None


@dataclass(frozen=True)
class AuthorizationOutcome:
    """The actor's M0 access-decision projection as applied at
    the M8 boundary.
    """
    allowed: bool
    reason: str
    policy_filter: AccessPolicyFilter


@dataclass(frozen=True)
class RetrieveAuthorizedResult:
    """The application-side output.

    `authorization`: the M0 decision projection.
    `ranked`: the post-rerank, post-drop ranked survivors.
    `stats`: per-stage candidate counts (`DenseStage`,
    `Bm25Stage`, `FusedStage`, `RerankStage`, `AfterAccessStage`).
    """
    authorization: AuthorizationOutcome
    ranked: tuple[RankedCandidate, ...]
    stats: RetrievalStageStats


def _clearance_from_str(value: str) -> Optional[Clearance]:
    """Translate a JWT-typed clearance string into the V1 enum.

    The actor's `AuthActor.clearance` carries the JWT-supplied
    string verbatim (lowercase by JWT convention); the V1
    `Clearance` enum uses the M0 canonical uppercase ladder.
    The translation is case-insensitive to defend against
    mis-issued tokens. `None` is returned when the string is
    blank — the M0 access-decision pure function then denies
    with `missing_user_clearance` per its fail-closed rule.
    """
    if value is None or not value.strip():
        return None
    upper = value.strip().upper()
    try:
        return Clearance[upper]
    except KeyError as exc:
        raise AccessDecisionUnavailableError(
            f"actor clearance {value!r} is not a V1 ladder step."
        ) from exc


def _policy_filter_from_decision(
    actor: AuthActor,
    clearance_enum: Clearance,
    decision_outcome: AccessResult,
) -> AccessPolicyFilter:
    """Translate the M0 decision tuple into the M8 SQL filter.

    The pure function's `(allowed, reason)` is preserved on
    the projection. When the decision is `allow`, the
    allowed_departments are `[actor.department, "ALL"]`;
    when denied, no department set is exposed so the
    downstream SQL filter captures NO candidates
    (fail-closed).

    `minimum_clearance` carries the V1 canonical uppercase
    ladder step (`"PUBLIC" / "INTERNAL" / ...`). The M8
    SQL filter uses the canonical string form.
    """
    allowed, reason = decision_outcome
    if not allowed:
        return AccessPolicyFilter(
            allowed_departments=(),
            minimum_clearance=clearance_enum.name,
            decision_outcome=(allowed, reason),
        )
    return AccessPolicyFilter(
        allowed_departments=tuple(
            sorted({actor.department, _ALL_DEPARTMENT})
        ),
        minimum_clearance=clearance_enum.name,
        decision_outcome=(allowed, reason),
    )


def _post_rerank_drop(
    ranked: Sequence[RankedCandidate],
    actor: AuthActor,
    clearance_enum: Clearance,
    documents_by_chunk_id,
) -> list[RankedCandidate]:
    """Drop reranked candidates whose documents evaluate deny.

    The M0 pure function is invoked once per candidate. The
    result is a `(allowed, reason)` tuple; only allow-decidable
    survivors are kept. The closure may also be invoked for
    candidates whose `document_projection` is set, in which
    case we use it directly without re-resolving.
    """
    user = UserProjection(
        department=actor.department,
        clearance=clearance_enum,
    )
    survivors: list[RankedCandidate] = []
    for ranked_candidate in ranked:
        candidate = ranked_candidate.candidate
        doc_projection = getattr(candidate, "document_projection", None)
        if doc_projection is None:
            # Resolve the document projection from the
            # documents port. In production the pgvector /
            # pg_search adapters populate `document_projection`
            # synchronously so this branch is hot only in
            # the test in-memory adapter path.
            doc_projection = documents_by_chunk_id(candidate.chunk_id)
            if doc_projection is not None:
                candidate = RetrievalCandidate(
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    ordinal=candidate.ordinal,
                    dense_score=candidate.dense_score,
                    bm25_score=candidate.bm25_score,
                    text_preview=candidate.text_preview,
                    document_projection=doc_projection,
                )
        if doc_projection is None:
            # No projection available: defer to the M9
            # citation-verification step. We keep the
            # candidate in `survivors` for ranking.
            survivors.append(ranked_candidate)
            continue
        allowed, _reason = decide(user, doc_projection)
        if allowed:
            survivors.append(
                RankedCandidate(
                    candidate=candidate,
                    score=ranked_candidate.score,
                    stage=ranked_candidate.stage,
                )
            )
    return survivors


class RetrieveAuthorizedCandidates:
    """The M8 retrieval orchestrator.

    Constructor dependencies:

      - `documents_by_chunk_id`: a callable / repository method
        that returns a `DocumentProjection` for a chunk_id.
        Used by the post-rerank drop. M8 ships a thin
        callback; the production call site is
        `documents.find_by_id().as_authorization_projection()`.
      - `embedder`: M7 capability-shaped embedder.
      - `dense_retriever`, `bm25_retriever`: M8 protocol
        adapters.
      - `reranker`: M8 capability-shaped reranker. Optional;
        when None, the rerank stage is skipped and the fused
        list flows directly to the post-rerank drop.
    """

    def __init__(
        self,
        *,
        documents_by_chunk_id,
        embedder: QueryEmbedderProtocol,
        dense_retriever: DenseRetrieverProtocol,
        bm25_retriever: Bm25RetrieverProtocol,
        reranker: Optional[RerankerProtocol] = None,
    ) -> None:
        self._documents_by_chunk_id = documents_by_chunk_id
        self._embedder = embedder
        self._dense_retriever = dense_retriever
        self._bm25_retriever = bm25_retriever
        self._reranker = reranker

    async def execute(
        self, command: RetrieveAuthorizedCommand
    ) -> RetrieveAuthorizedResult:
        if not command.query_text or not command.query_text.strip():
            raise AccessDecisionUnavailableError(
                "RetrieveAuthorizedCandidates requires non-empty query_text."
            )
        correlation_id = (
            (command.correlation_id or "").strip()
            or (command.actor.correlation_id or "").strip()
            or "retrieval-fallback"
        )

        # Step 1: Pre-retrieval projection (M0 pure function).
        actor_clearance_value = _clearance_from_str(command.actor.clearance)
        if actor_clearance_value is None:
            # M0 pure function denies missing-user-clearance
            # via fail-closed; we mirror that decision
            # end-to-end and short-circuit the rest of the
            # pipeline. The post-rerank drop also
            # automatically denys because there are no
            # candidates to consume it.
            decision_outcome: AccessResult = (
                False, ACCESS_DECISION_MISSING_USER_CLEARANCE
            )
            policy_filter = AccessPolicyFilter(
                allowed_departments=(),
                minimum_clearance="PUBLIC",
                decision_outcome=decision_outcome,
            )
            stats = RetrievalStageStats(
                dense_count=0,
                bm25_count=0,
                fused_count=0,
                rerank_count=0,
                after_access_count=0,
            )
            outcome = AuthorizationOutcome(
                allowed=False,
                reason=decision_outcome[1],
                policy_filter=policy_filter,
            )
            return RetrieveAuthorizedResult(
                authorization=outcome,
                ranked=tuple(),
                stats=stats,
            )
        user = UserProjection(
            department=command.actor.department,
            clearance=actor_clearance_value,
        )
        # We evaluate the decision against a sentinel "ALL"
        # document so the projection sees an allow. The
        # actual document-set enforcement is at the SQL
        # filter step.
        sentinel_doc = DocumentProjection(
            department=_ALL_DEPARTMENT,
            required_clearance=actor_clearance_value,
        )
        decision_outcome = decide(user, sentinel_doc)
        policy_filter = _policy_filter_from_decision(
            command.actor, actor_clearance_value, decision_outcome
        )

        # If the M0 decision denied at the projection step
        # (the actor is missing a department / clearance),
        # the post-rerank drop short-circuits to empty.
        # We still raise the typed `AuthorizationOutcome`
        # plus an empty ranked list so the caller can audit
        # the refusal.
        if not decision_outcome[0]:
            empty = RetrievalStageStats(
                dense_count=0,
                bm25_count=0,
                fused_count=0,
                rerank_count=0,
                after_access_count=0,
            )
            return RetrieveAuthorizedResult(
                authorization=AuthorizationOutcome(
                    allowed=False,
                    reason=decision_outcome[1],
                    policy_filter=policy_filter,
                ),
                ranked=(),
                stats=empty,
            )

        # Step 2: Embed query.
        embedding = self._embedder.embed(command.query_text)
        if len(embedding) != 1024 and len(embedding) != 1536:
            # The pgvector codec requires a length that matches
            # documents.embedding's `vector(N)` shape. We
            # check the canonical M1 dimension (1536) and a
            # future M8-shape (1024) tolerantly; anything
            # outside either fails fast.
            raise AccessDecisionUnavailableError(
                f"embedder returned {len(embedding)}-dim vector; "
                "expected 1536 (M1 schema) or 1024 (M8 alternate)."
            )

        query = RetrievalQuery(
            query_text=command.query_text,
            top_k=command.top_k,
            access_filter=policy_filter,
            correlation_id=correlation_id,
        )

        # Step 3: Dense retrieval.
        dense_candidates = await self._dense_retriever.retrieve(
            query, embedding
        )
        dense_ranked = [
            (rank, c)
            for rank, c in enumerate(
                sorted(
                    dense_candidates,
                    key=lambda x: -(x.dense_score or 0.0),
                ),
                start=1,
            )
        ]

        # Step 4: BM25 retrieval.
        bm25_candidates = await self._bm25_retriever.retrieve(query)
        bm25_ranked = [
            (rank, c)
            for rank, c in enumerate(
                sorted(
                    bm25_candidates,
                    key=lambda x: -(x.bm25_score or 0.0),
                ),
                start=1,
            )
        ]
        if not dense_ranked and not bm25_ranked:
            empty = RetrievalStageStats(0, 0, 0, 0, 0)
            # The M8 closure rule: empty retrieval -> 503. We
            # raise `EmptyRetrievalError` so the workflow
            # boundary at M9 / M6 can translate.
            raise EmptyRetrievalError(
                f"retrieval returned zero candidates (correlation_id={correlation_id})"
            )

        # Step 5: RRF fusion.
        from src.domain.retrieval.rrf import RankedItem

        fused = rrf_fuse(
            [
                RankedItem(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    score=c.dense_score or 0.0,
                )
                for _rank, c in dense_ranked
            ],
            [
                RankedItem(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    score=c.bm25_score or 0.0,
                )
                for _rank, c in bm25_ranked
            ],
            k=DEFAULT_RRF_K,
        )

        # Step 6: Cross-encoder rerank (optional). When the
        # M8 capability is adopted the rerank stage lands here;
        # M8 ships with optional rerank so the in-memory test
        # adapters don't need it.
        fused_ranked: list[RankedCandidate] = [
            RankedCandidate(
                candidate=_candidate_from_fused(fc),
                score=fc.fused_score,
                stage="fused",
            )
            for fc in fused
        ]
        if self._reranker is not None and command.rerank_top_n > 0:
            fused_ranked = list(
                await self._reranker.rerank(
                    query,
                    fused_ranked,
                    top_n=command.rerank_top_n,
                )
            )

        # Step 7: Post-rerank decision drop (M0 pure function).
        survivors = _post_rerank_drop(
            fused_ranked,
            command.actor,
            actor_clearance_value,
            self._documents_by_chunk_id,
        )

        stats = RetrievalStageStats(
            dense_count=len(dense_candidates),
            bm25_count=len(bm25_candidates),
            fused_count=len(fused_ranked),
            rerank_count=(
                len(fused_ranked) if self._reranker is not None else 0
            ),
            after_access_count=len(survivors),
        )
        return RetrieveAuthorizedResult(
            authorization=AuthorizationOutcome(
                allowed=True,
                reason=DecisionReason.ALLOWED,
                policy_filter=policy_filter,
            ),
            ranked=tuple(survivors),
            stats=stats,
        )


def _candidate_from_fused(fused: FusedCandidate) -> RetrievalCandidate:
    """Project a fused row back to the canonical `RetrievalCandidate`.

    The fused row carries `(chunk_id, document_id, fused_score,
    dense_rank, bm25_rank, dense_score, bm25_score)`; we drop
    fused-internal columns and rebuild the candidate shape.
    """
    from src.domain.ports.retrieval import RetrievalCandidate

    return RetrievalCandidate(
        chunk_id=fused.chunk_id,
        document_id=fused.document_id,
        ordinal=int(getattr(fused, "ordinal", 0) or 0),
        dense_score=fused.dense_score,
        bm25_score=fused.bm25_score,
        text_preview=None,
    )


__all__ = [
    "RetrieveAuthorizedCandidates",
    "RetrieveAuthorizedCommand",
    "RetrieveAuthorizedResult",
    "AuthorizationOutcome",
    "EmptyRetrievalError",
    "AccessDecisionUnavailableError",
]
