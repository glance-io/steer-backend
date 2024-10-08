from enum import Enum


class Tier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    LIFETIME = "lifetime"

    def __str__(self):
        return self.value