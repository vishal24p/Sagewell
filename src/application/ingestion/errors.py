"""Typed-error hierarchy for the M7 ingestion application.

Boundary contract:

  - `IngestionDomainError` is the application-side base.
    Every application error that is NOT a persistence failure
    is reported via this exception.

  - `IngestionPipelineError(IngestionDomainError)` covers
    failures that originate from the chunks / documents
    repositories or from the chunker / embedder. The use case
    catches these only to translate them into a failure-shaped
    audit row and an `IngestOutcome.FAILED` return; it does
    NOT swallow them. The exception keeps its message and type.

  - The `code` slug is the stable identifier for the failure
    path. Tests assert on the slug, not on the message text.
"""
from __future__ import annotations


class IngestionDomainError(Exception):
    """Base for every ingestion application error."""

    code: str = "ingestion_failed"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.__class__.__name__)


class IngestionPipelineError(IngestionDomainError):
    """Pipeline-side failure: chunker / embedder / repository."""

    code: str = "ingestion_pipeline_error"


class MissingContentError(IngestionDomainError):
    """The supplied document content is blank."""

    code: str = "missing_content"


class EmbeddingShapeMismatchError(IngestionDomainError):
    """The embedder returned a vector of unexpected length."""

    code: str = "embedding_shape_mismatch"


__all__ = [
    "IngestionDomainError",
    "IngestionPipelineError",
    "MissingContentError",
    "EmbeddingShapeMismatchError",
]
