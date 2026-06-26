"""Content-checksum helper.

The M7 ingestion path must be idempotent on `documents.content_checksum`.
The canonical checksum is computed by normalizing the supplied raw
content (stripping carriage returns + trailing whitespace, collapsing
internal blank lines) and hashing it with sha256. The choice below
keeps the checksum stable across editors and platforms; M1 fixtures
recomputed through the same function yield identical strings.

`normalize_content_checksum(text, *, hash_fn=hashlib.sha256)` is
parameterized so tests can use a deterministic stub.
"""
from __future__ import annotations

import hashlib
import re
from typing import Callable


_HASH_FN = hashlib.sha256
_CHECKSUM_LENGTH = 64  # hex(sha256) length


def _normalize(text: str) -> str:
    # Strip CR characters so Windows-style newlines normalize to LF.
    stripped = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse trailing whitespace on each line.
    stripped = "\n".join(line.rstrip() for line in stripped.split("\n"))
    # Collapse 3+ consecutive blank lines into a single blank line.
    stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    # Trim leading and trailing blank lines.
    return stripped.strip()


def normalize_content_checksum(
    text: str,
    *,
    hash_fn: Callable[..., "_HashLike"] = _HASH_FN,
) -> str:
    """Return a stable idempotence key for the supplied raw content."""
    normalized = _normalize(text)
    digest = hash_fn(normalized.encode("utf-8")).hexdigest()
    return digest


__all__ = ["normalize_content_checksum", "_CHECKSUM_LENGTH"]


# Internal type alias preserved for IDE hints. `_HashLike` behaves like
# hashlib's hash objects without dragging the type into public surface.
class _HashLike:
    def update(self, data: bytes) -> None: ...
    def hexdigest(self) -> str: ...
