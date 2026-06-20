"""
TRUNCATE ... RESTART IDENTITY CASCADE per-test isolation for the
Postgres adapters.

CI/dev workflow:
  * open the pool once per test session;
  * call `truncate_all_tables(...)` in an autouse fixture's
    teardown so each test starts from a clean slate;
  * do NOT depend on `pg_hba.conf`-friendly credentials beyond
    what the dev compose already grants.
"""
from __future__ import annotations

import asyncpg


_V1_TABLES_IN_RESET_ORDER = (
    "audit_logs",
    "retrieval_logs",
    "evaluation_results",
    "chunks",
    "documents",
    "users",
)


async def truncate_all_tables(pool: asyncpg.Pool) -> None:
    """Reset every V1 table to an empty state.

    Order is FK-safe: children are truncated before parents. The
    CASCADE flag covers FK RESTRICT parents because TRUNCATE...
    CASCADE bypasses per-table constraints during reset.
    """
    sql = (
        "TRUNCATE TABLE "
        + ", ".join(_V1_TABLES_IN_RESET_ORDER)
        + " RESTART IDENTITY CASCADE"
    )
    async with pool.acquire() as conn:
        await conn.execute(sql)
