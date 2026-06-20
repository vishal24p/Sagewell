"""
Repositories parity test configuration.

  * The session-scoped `adapter`-parameterized fixture yields two
    factory functions: in-memory and Postgres. Each test invokes
    the factory to build fresh adapters; Postgres tests truncate
    the V1 tables between tests so the test matrix starts from
    a clean slate.
  * Postgres tests are skipped when `SAGEWELL_DB_URL` is unset
    or unreachable. The sandbox does not start Docker; CI/dev
    sets the variable and activates the postgres path.
  * `pytest-asyncio` global `asyncio_mode = "auto"` keeps each
    async function pytest-awaiting without explicit markers.

The goal is that the same repository test matrix runs against
both adapters without code duplication.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import AsyncIterator, Callable

import asyncpg
import pytest

from src.domain.ports.audit_logs import AuditLogRepository
from src.domain.ports.chunks import ChunkRepository
from src.domain.ports.clearances import Clearance
from src.domain.ports.documents import Document, DocumentRepository, DocumentStatus
from src.domain.ports.evaluation_results import EvaluationResultRepository
from src.domain.ports.retrieval_logs import RetrievalLogRepository
from src.domain.ports.users import User, UserRepository, UserRole, UserStatus

from src.infrastructure.repositories.in_memory.audit_logs import (
    InMemoryAuditLogRepository,
)
from src.infrastructure.repositories.in_memory.chunks import (
    InMemoryChunkRepository,
)
from src.infrastructure.repositories.in_memory.documents import (
    InMemoryDocumentRepository,
)
from src.infrastructure.repositories.in_memory.evaluation_results import (
    InMemoryEvaluationResultRepository,
)
from src.infrastructure.repositories.in_memory.retrieval_logs import (
    InMemoryRetrievalLogRepository,
)
from src.infrastructure.repositories.in_memory.users import (
    InMemoryUserRepository,
)


from src.infrastructure.repositories.postgres.users import (
    PostgresUserRepository,
)
from src.infrastructure.repositories.postgres.documents import (
    PostgresDocumentRepository,
)
from src.infrastructure.repositories.postgres.chunks import (
    PostgresChunkRepository,
)
from src.infrastructure.repositories.postgres.audit_logs import (
    PostgresAuditLogRepository,
)
from src.infrastructure.repositories.postgres.retrieval_logs import (
    PostgresRetrievalLogRepository,
)
from src.infrastructure.repositories.postgres.evaluation_results import (
    PostgresEvaluationResultRepository,
)
from src.infrastructure.repositories.postgres.reset import (
    truncate_all_tables,
)


Backend = str  # "in_memory" or "postgres"

_PARENT_USER_AT = datetime(2026, 6, 19, tzinfo=timezone.utc)
_PARENT_DOC_AT = _PARENT_USER_AT


# ---------------------------------------------------------------------
# Postgres session fixture: opens a pool once per session if reachable.
# ---------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_dsn() -> str:
    """Return the runtime DSN. Empty string means postgres is unavailable."""
    return os.environ.get("SAGEWELL_DB_URL", "")


@pytest.fixture
async def postgres_pool(db_dsn: str) -> AsyncIterator[asyncpg.Pool]:
    """Open the asyncpg pool per-test so its connections bind to the
    active event loop.

    pytest-asyncio 1.x with `asyncio_mode = "auto"` resolves each
    test to its own event loop. asyncpg pools hold connections
    whose protocol is bound to the loop that first acquired them,
    so a session-scoped pool produces cross-loop `InterfaceError`
    symptoms on the second and later postgres tests. Function
    scope is the explicit, predictable fix until we add a global
    `asyncio_default_fixture_loop_scope = "session"` config.

    Skips the entire postgres-half suite when the sandbox does
    not expose a database.
    """
    if not db_dsn:
        pytest.skip("SAGEWELL_DB_URL not set; postgres parity tests skipped")

    from src.infrastructure.repositories.postgres.pool import (
        default_pool_factory,
    )

    try:
        pool = await default_pool_factory(db_dsn)()
    except (OSError, asyncpg.PostgresError) as exc:
        pytest.skip(f"postgres connection failed: {exc!r}")

    try:
        yield pool
    finally:
        await pool.close()


@pytest.fixture
async def clean_postgres_state(postgres_pool: asyncpg.Pool) -> AsyncIterator[None]:
    """TRUNCATE ... RESTART IDENTITY CASCADE before each postgres test.

    Reads no `request.param`; the fixture unconditionally resets
    the V1 tables. Postgres connectivity is handled by the
    `postgres_pool` fixture (skip-on-unreachable).
    """
    await truncate_all_tables(postgres_pool)
    yield


# ---------------------------------------------------------------------
# Adapter factory: parametrized over Backend.
# ---------------------------------------------------------------------

AdapterFactory = Callable[
    [asyncpg.Pool | None],
    tuple[
        UserRepository,
        DocumentRepository,
        ChunkRepository,
        AuditLogRepository,
        RetrievalLogRepository,
        EvaluationResultRepository,
    ],
]


def _in_memory_factory(_pool: asyncpg.Pool | None) -> tuple[
    UserRepository,
    DocumentRepository,
    ChunkRepository,
    AuditLogRepository,
    RetrievalLogRepository,
    EvaluationResultRepository,
]:
    return (
        InMemoryUserRepository(),
        InMemoryDocumentRepository(),
        InMemoryChunkRepository(),
        InMemoryAuditLogRepository(),
        InMemoryRetrievalLogRepository(),
        InMemoryEvaluationResultRepository(),
    )


def _postgres_factory(pool: asyncpg.Pool | None) -> tuple[
    UserRepository,
    DocumentRepository,
    ChunkRepository,
    AuditLogRepository,
    RetrievalLogRepository,
    EvaluationResultRepository,
]:
    assert pool is not None, "postgres factory called with no pool"
    return (
        PostgresUserRepository(pool),
        PostgresDocumentRepository(pool),
        PostgresChunkRepository(pool),
        PostgresAuditLogRepository(pool),
        PostgresRetrievalLogRepository(pool),
        PostgresEvaluationResultRepository(pool),
    )


@pytest.fixture(
    params=["in_memory", "postgres"],
    ids=lambda v: v,
)
def adapter(request):
    """
    Parametrized adapter selector.

    Yields the backend string. Tests that need the factory pull it
    through `request.getfixturevalue(...)` against the chosen param.
    """
    backend: Backend = request.param
    if backend == "postgres":
        return backend, _postgres_factory, request.getfixturevalue("postgres_pool")
    return backend, _in_memory_factory, None


@pytest.fixture
def repos(adapter):
    """Convenience fixture: yield `(backend, factory, repos_tuple)`.

    Postgres paths additionally depend on `clean_postgres_state`
    being listed by the test's parameter list.
    """
    backend, factory, pool = adapter
    return backend, factory, factory(pool)


# ---------------------------------------------------------------------
# Cross-test parent-row seeding helper.
#
# `audit_logs.actor_user_id`, `retrieval_logs.actor_user_id`, and
# `chunks.document_id` all have FK RESTRICT to their respective
# parents. Tests must therefore have user id=1 and document id=42
# already present in the active backend. This fixture seeds both
# rows before each test that depends on it.
# ---------------------------------------------------------------------

@pytest.fixture
async def seed_parent_rows(adapter, clean_postgres_state):
    backend, factory, pool = adapter
    user_repo, doc_repo, *_ = factory(pool)
    if pool is None:
        user_repo.add(
            User(
                id=1,
                external_subject="subject-parent",
                email="parent@example.com",
                display_name="Parent User",
                status=UserStatus.ACTIVE,
                department="finance",
                clearance=Clearance.CONFIDENTIAL,
                role=UserRole.EMPLOYEE,
                created_at=_PARENT_USER_AT,
                updated_at=_PARENT_USER_AT,
            )
        )
        doc_repo.add(
            Document(
                id=42,
                source_system="fixture",
                source_id="doc-parent",
                title="Parent Document",
                uri=None,
                status=DocumentStatus.ACTIVE,
                department="finance",
                required_clearance=Clearance.INTERNAL,
                content_checksum="checksum-parent",
                created_at=_PARENT_DOC_AT,
                updated_at=_PARENT_DOC_AT,
            )
        )
    else:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (
                  id, external_subject, email, display_name,
                  status, department, clearance, role,
                  created_at, updated_at
                ) VALUES (
                  1, 'subject-parent', 'parent@example.com',
                  'Parent User', 'active', 'finance',
                  'CONFIDENTIAL', 'employee',
                  $1, $2
                )
                """,
                _PARENT_USER_AT,
                _PARENT_USER_AT,
            )
            await conn.execute(
                """
                INSERT INTO documents (
                  id, source_system, source_id, title, uri,
                  status, department, required_clearance,
                  content_checksum, created_at, updated_at
                ) VALUES (
                  42, 'fixture', 'doc-parent', 'Parent Document',
                  NULL, 'active', 'finance', 'INTERNAL',
                  'checksum-parent', $1, $2
                )
                """,
                _PARENT_DOC_AT,
                _PARENT_DOC_AT,
            )
    return backend
