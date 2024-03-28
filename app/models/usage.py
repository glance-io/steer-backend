import datetime

from pydantic import BaseModel as PydanticBaseModel


class CurrentUsage(PydanticBaseModel):
    quantity: int
    period_start: datetime.datetime
    period_end: datetime.datetime
