"""
Postgres-backed implementations of the repository ports.

This module also owns the asyncpg connection-pool factory used by
the Postgres adapters and the parity tests. The factory:

  * configures the JSONB codec so dicts round-trip with the
    `audit_logs.metadata`, `retrieval_logs.*_json` and
    `evaluation_results.*_json` columns;
  * registers the `pgvector` codec so chunks.embedding round-trips
    as a Python list[float] of length EMBEDDING_DIM;
  * rejects connections to unrelated databases.

Authoring-only: the M1 verification report places the dev compose
on localhost:55432 with the same credentials. The Postgres
adapters are the production implementation; the in-memory
implementation is the reference.
"""
from .users import PostgresUserRepository
from .documents import PostgresDocumentRepository
from .chunks import PostgresChunkRepository
from .audit_logs import PostgresAuditLogRepository
from .retrieval_logs import PostgresRetrievalLogRepository
from .evaluation_results import PostgresEvaluationResultRepository
from .pool import PoolFactory, default_pool_factory
from .reset import truncate_all_tables


__all__ = [
    "PostgresUserRepository",
    "PostgresDocumentRepository",
    "PostgresChunkRepository",
    "PostgresAuditLogRepository",
    "PostgresRetrievalLogRepository",
    "PostgresEvaluationResultRepository",
    "PoolFactory",
    "default_pool_factory",
    "truncate_all_tables",
]
