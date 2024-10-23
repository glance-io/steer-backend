from datetime import datetime

from pydantic import BaseModel as PydanticBaseModel


class StatsResDTO(PydanticBaseModel):
    usage: str
