"""
Parity tests for UserRepository.

The same test matrix runs against the in-memory and Postgres
adapters. Postgres tests skip when SAGEWELL_DB_URL is unset.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.domain.ports.clearances import Clearance
from src.domain.ports.users import User, UserRole, UserStatus


def _user_row(id: int = 1) -> dict:
    """Raw row dict for the test seeding path."""
    return {
        "id": id,
        "external_subject": f"subject-{id}",
        "email": f"user-{id}@example.com",
        "display_name": f"User {id}",
        "status": "active",
        "department": "finance",
        "clearance": "CONFIDENTIAL",
        "role": "employee",
        "created_at": datetime(2026, 6, 19, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 6, 19, tzinfo=timezone.utc),
    }


async def _seed_user(users_repo, raw: dict, pool=None) -> None:
    """Seed `users` against the active backend."""
    if pool is None:
        # in-memory: use add().
        users_repo.add(
            User(
                id=raw["id"],
                external_subject=raw["external_subject"],
                email=raw["email"],
                display_name=raw["display_name"],
                status=UserStatus(raw["status"]),
                department=raw["department"],
                clearance=Clearance[raw["clearance"]],
                role=UserRole(raw["role"]) if raw["role"] else None,
                created_at=raw["created_at"],
                updated_at=raw["updated_at"],
            )
        )
    else:
        # Postgres: INSERT directly through the pool.
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (
                  id, external_subject, email, display_name,
                  status, department, clearance, role,
                  created_at, updated_at
                ) VALUES (
                  $1,$2,$3,$4,$5,$6,$7,$8,$9,$10
                )
                """,
                raw["id"],
                raw["external_subject"],
                raw["email"],
                raw["display_name"],
                raw["status"],
                raw["department"],
                raw["clearance"],
                raw["role"],
                raw["created_at"],
                raw["updated_at"],
            )


class TestUserRepository:
    @pytest.fixture
    async def setup(self, adapter, clean_postgres_state):
        backend, factory, pool = adapter
        user_repo, *_ = factory(pool)
        await _seed_user(user_repo, _user_row(1), pool)
        return backend, user_repo, pool

    async def test_find_by_id_returns_seeded_row(self, setup):
        backend, repo, _pool = setup
        user = await repo.find_by_id(1)
        assert user is not None
        assert user.id == 1
        assert user.external_subject == "subject-1"
        assert user.department == "finance"
        assert user.clearance == Clearance.CONFIDENTIAL
        assert user.role == UserRole.EMPLOYEE
        assert user.status == UserStatus.ACTIVE

    async def test_find_by_id_returns_None_when_missing(self, setup):
        _backend, repo, _pool = setup
        user = await repo.find_by_id(999)
        assert user is None

    async def test_find_by_external_subject(self, setup):
        _backend, repo, _pool = setup
        user = await repo.find_by_external_subject("subject-1")
        assert user is not None
        assert user.email == "user-1@example.com"

    async def test_find_by_external_subject_returns_None_when_missing(self, setup):
        _backend, repo, _pool = setup
        user = await repo.find_by_external_subject("nobody")
        assert user is None
