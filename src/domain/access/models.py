from dataclasses import dataclass
from typing import Optional

from .clearances import Clearance


# `role` mirrors `users.role` for UI behavior and auditing only.
# It MUST NOT participate in authorization.
@dataclass(frozen=True)
class User:
    department: Optional[str]
    clearance: Optional[Clearance]
    role: Optional[str] = None


# `department == "ALL"` is the company-wide escape for documents.
# `users.role` does not appear here; there is no authorization field
# for it.
@dataclass(frozen=True)
class Document:
    department: Optional[str]
    required_clearance: Optional[Clearance]
