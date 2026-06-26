"""M7 `DocumentChunkerProtocol` LlamaIndex-backed implementation.

Wraps LlamaIndex's `SentenceSplitter` (M7 default chunker).
The infrastructure adapter is the only place that imports
`llama_index`; the application layer sees only the
`DocumentChunkerProtocol`.

Boundary contract:

| Concern                          | Application sees        | Implementation lives                                        |
|----------------------------------|-------------------------|------------------------------------------------------------|
| Document textual granularity     | `Sequence[ChunkSegment]` | LlamaIndex `SentenceSplitter`                            |
| Chunk metadata shape             | `dict`                  | `{ordinal, start_char, end_char}` from the parsed node     |
| Skip pure-whitespace chunks      | always                  | always                                                      |
| Empty / blank document           | empty sequence          | empty sequence                                              |

`LlamaIndexChunkerConfig` carries the capability-based knobs
(chunk_size, chunk_overlap). These are deliberately held at
the adapter layer; the application use case does not know
about them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from src.domain.ports.ingestion import ChunkSegment, DocumentChunkerProtocol


@dataclass(frozen=True)
class LlamaIndexChunkerConfig:
    """Capability-based knob holder for the LlamaIndex chunker.

    `chunk_size` is the approximate character budget for each
    chunk (LlamaIndex accepts text splitter options based on
    tokens or sentences; this adapter exposes the character's
    baseline for V1). `chunk_overlap` is the overlap between
    consecutive chunks; 0 is the M7 default because the
    ingestion use case treats every chunk as independent for
    the M8 dense retrieval contract.
    """

    chunk_size: int = 256
    chunk_overlap: int = 0


class LlamaIndexChunker(DocumentChunkerProtocol):
    """LlamaIndex-backed `DocumentChunkerProtocol` implementation.

    The adapter is constructed with a `LlamaIndexChunkerConfig`
    and lazily imports `llama_index.core.node_parser` so a
    sandbox without LlamaIndex does not pay the import cost
    at module load.
    """

    def __init__(self, config: LlamaIndexChunkerConfig | None = None) -> None:
        self._config = config or LlamaIndexChunkerConfig()

    def chunk(self, text: str) -> Sequence[ChunkSegment]:
        if not text or not text.strip():
            return []
        from llama_index.core.node_parser import SentenceSplitter

        splitter = SentenceSplitter(
            chunk_size=self._config.chunk_size,
            chunk_overlap=self._config.chunk_overlap,
        )
        # LlamaIndex returns a list[str]; each element is a chunk.
        segments: list[ChunkSegment] = []
        for ordinal, chunk_text in enumerate(splitter.split_text(text)):
            if not chunk_text.strip():
                continue
            segments.append(
                ChunkSegment(
                    ordinal=ordinal,
                    text=chunk_text,
                    metadata={
                        "ordinal": ordinal,
                        "length": len(chunk_text),
                    },
                )
            )
        return segments


__all__ = ["LlamaIndexChunker", "LlamaIndexChunkerConfig"]
