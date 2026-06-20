"""
V1 User aggregate and UserRepository port.

The User aggregate is the full database-shaped V1 record. The
access-decision pure function consumes only the M0 access
projection (`User.department`, `User.clearance`, optionally
`User.role`). Use `User.as_authorization_projection()` to adapt.

Status / Role values are string-valued enums so Postgres TEXT
columns round-trip without separate codec mapping. The adapter
rejects unknown strings by raising PersistenceError.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Protocol

from .clearances import Clearance


class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class UserRole(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    ADMIN = "admin"


@dataclass(frozen=True)
class User:
    id: int
    external_subject: str
    email: str
    display_name: str
    status: UserStatus
    department: str
    clearance: Clearance
    role: Optional[UserRole]
    created_at: datetime
    updated_at: datetime

    def as_authorization_projection(self) -> "UserProjection":
        """Return the M0 access-decision projection of this user.

        The access-decision pure function takes a minimal view of
        the user record (department, clearance, role). Use this
        adapter at the boundary.
        """
        return UserProjection(
            department=self.department,
            clearance=self.clearance,
            role=self.role.value if self.role is not None else None,
        )


@dataclass(frozen=True)
class UserProjection:
    """The minimal projection the access-decision pure function uses.

    Not a port; not a Protocol. Lives here because the access
    boundary (must produce this shape) is stable; M0's mapping
    tests rely on it.
    """
    department: Optional[str]
    clearance: Optional[Clearance]
    role: Optional[str] = None


class UserRepository(Protocol):
    async def find_by_id(self, user_id: int) -> Optional[User]: ...

    async def find_by_external_subject(self, external_subject: str) -> Optional[User]: ...
