"""
Repository-tier exceptions.

`PersistenceError` is raised on infrastructure write/read failures
(Postgres connection lost, unique-violation when explicitly
forbidden, JSON marshalling failure).
`ResourceNotFound` is raised only when the implementation chooses
the "raise" negative-case contract instead of returning `None`;
neither repository in M2 raises ResourceNotFound; `find_*` methods
return `None` when no row matches the criterion.
"""
from typing import Optional


class DomainError(Exception):
    """Base class for repository-tier and access-decision errors."""


class PersistenceError(DomainError):
    """Raised on infrastructure write/read failures."""

    def __init__(self, message: str, *, cause: Optional[BaseException] = None):
        super().__init__(message)
        self.__cause__ = cause


class ResourceNotFound(DomainError):
    """Raised when a lookup expected exactly one row and got zero."""

    def __init__(self, resource: str, identifier: object):
        super().__init__(f"{resource} not found: {identifier!r}")
        self.resource = resource
        self.identifier = identifier
