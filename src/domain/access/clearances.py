from enum import IntEnum


class Clearance(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3

    def is_at_least(self, required: "Clearance") -> bool:
        return int(self) >= int(required)
