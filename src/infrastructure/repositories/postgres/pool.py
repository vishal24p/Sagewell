"""
asyncpg pool factory with JSONB and pgvector codec registration.

The codecs are wired through the `init` argument of
`asyncpg.create_pool(...)`. Each connection that the pool hands
out has the codecs already registered before any query runs.

The DSN is supplied at runtime via the `SAGEWELL_DB_URL`
environment variable. The default DSN documented in
infrastructure/migrations/README.md references the same dev
compose port (55432) but is intentionally absent from this
source so no credentials leak into the repository.
"""
from __future__ import annotations

import json
import os
from typing import Awaitable, Callable, Optional

import asyncpg

from src.domain.ports.chunks import EMBEDDING_DIM


DEFAULT_DB_URL = os.environ.get("SAGEWELL_DB_URL", "")


PoolFactory = Callable[[], Awaitable[asyncpg.Pool]]


async def _init_connection(connection: asyncpg.Connection) -> None:
    """asyncpg per-connection init: JSONB + json codecs, then pgvector."""
    await connection.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await connection.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    from pgvector.asyncpg import register_vector

    await register_vector(connection)


async def _make_pool(
    dsn: Optional[str] = None,
    *,
    min_size: int = 1,
    max_size: int = 8,
) -> asyncpg.Pool:
    if not (dsn or DEFAULT_DB_URL):
        raise RuntimeError(
            "SAGEWELL_DB_URL must be set to a psql-style connection URL."
        )
    return await asyncpg.create_pool(
        dsn=dsn or DEFAULT_DB_URL,
        min_size=min_size,
        max_size=max_size,
        init=_init_connection,
    )


def default_pool_factory(dsn: Optional[str] = None) -> PoolFactory:
    """Build a PoolFactory that opens a pool with codecs registered.

    Returns a callable that yields a fresh pool. The caller is
    responsible for closing the pool when the test session
    finishes. The pool is one-and-done per process.
    """

    async def _factory() -> asyncpg.Pool:
        return await _make_pool(dsn)

    return _factory


__all__ = ["EMBEDDING_DIM", "PoolFactory", "default_pool_factory", "DEFAULT_DB_URL"]
