from enum import Enum

from pydantic import BaseModel


class DBConfig(BaseModel):
    url: str
    password: str


class ThrottlingPeriod(str, Enum):
    DAILY = ("daily", 1)
    WEEKLY = ("weekly", 7)

    def __new__(cls, value, days):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.days = days
        return obj

    def __str__(self):
        return self.value


class ThrottlingConfig(BaseModel):
    limit: int
    period: ThrottlingPeriod
