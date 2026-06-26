"""M7 ingestion application package.

The ingestion use case is exercised in-process at M7 (no
background worker, no `/v1/*` endpoint). The connector-driven
job lands here. Future M13+, if a connector schedule is
introduced, runs through the same use case.
"""
from __future__ import annotations

from src.application.ingestion.errors import (
    IngestionDomainError,
    IngestionPipelineError,
)
from src.application.ingestion.ingest import (
    IngestDocument,
    IngestDocumentCommand,
    IngestOutcome,
)
from src.application.ingestion.checksum import normalize_content_checksum


__all__ = [
    "IngestDocument",
    "IngestDocumentCommand",
    "IngestOutcome",
    "IngestionDomainError",
    "IngestionPipelineError",
    "normalize_content_checksum",
]
