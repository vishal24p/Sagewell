"""
V1 Clearance ladder.

PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED. Higher integer values
have higher clearance. The access-decision function compares the
actor's clearance against the document's required_clearance using
`is_at_least`.

The M0 RBAC Access Outcome Suite imports Clearance from here.
"""
from enum import IntEnum


class Clearance(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3

    def is_at_least(self, required: "Clearance") -> bool:
        return int(self) >= int(required)
