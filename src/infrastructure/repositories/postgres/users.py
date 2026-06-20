"""
Postgres-backed UserRepository.

The migration creates enum-shaped TEXT columns. The adapter
coerces valid strings to the domain enums and raises
PersistenceError on unknown values.
"""
from __future__ import annotations

from typing import Optional

import asyncpg

from src.domain.ports.clearances import Clearance
from src.domain.ports.errors import PersistenceError
from src.domain.ports.users import User, UserRepository, UserRole, UserStatus


_CLEARANCE_BY_TEXT = {
    "PUBLIC": Clearance.PUBLIC,
    "INTERNAL": Clearance.INTERNAL,
    "CONFIDENTIAL": Clearance.CONFIDENTIAL,
    "RESTRICTED": Clearance.RESTRICTED,
}


def _coerce_user(row: asyncpg.Record) -> User:
    try:
        status = UserStatus(row["status"])
    except ValueError as exc:
        raise PersistenceError(
            f"users.status is not a V1 status: {row['status']!r}"
        ) from exc
    clearance = _CLEARANCE_BY_TEXT.get(row["clearance"])
    if clearance is None:
        raise PersistenceError(
            f"users.clearance is not a V1 clearance: {row['clearance']!r}"
        )
    role_value = row["role"]
    role: Optional[UserRole] = None
    try:
        if role_value is not None:
            role = UserRole(role_value)
    except ValueError as exc:
        raise PersistenceError(
            f"users.role is not a V1 role: {role_value!r}"
        ) from exc
    return User(
        id=row["id"],
        external_subject=row["external_subject"],
        email=row["email"],
        display_name=row["display_name"],
        status=status,
        department=row["department"],
        clearance=clearance,
        role=role,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresUserRepository(UserRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_id(self, user_id: int) -> Optional[User]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                user_id,
            )
        return _coerce_user(row) if row is not None else None

    async def find_by_external_subject(self, external_subject: str) -> Optional[User]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE external_subject = $1",
                external_subject,
            )
        return _coerce_user(row) if row is not None else None
