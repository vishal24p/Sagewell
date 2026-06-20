"""
In-memory UserRepository.

Stores full User aggregates in a dict keyed by id. All async
methods run synchronously inside the asyncio event loop.
"""
from collections import defaultdict
from typing import Optional

from src.domain.ports.errors import PersistenceError
from src.domain.ports.users import User, UserRepository


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        # Concurrent-safe in CPython because each test runs in the
        # single event loop; no Lock is added here.
        self._users: dict[int, User] = {}

    def add(self, user: User) -> User:
        """Helper for tests. Caller fully owns the row shape."""
        if user.id in self._users:
            raise PersistenceError(f"user id conflict: {user.id}")
        self._users[user.id] = user
        return user

    async def find_by_id(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    async def find_by_external_subject(self, external_subject: str) -> Optional[User]:
        for user in self._users.values():
            if user.external_subject == external_subject:
                return user
        return None
