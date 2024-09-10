from enum import Enum
from typing import Optional

from pydantic import BaseModel as PydanticBaseModel


class RephraseTaskType(str, Enum):
    FIX_GRAMMAR = "fix_grammar"
    REPHRASE = "rephrase"
    CONCISE = "concise"


class RephraseRequest(PydanticBaseModel):
    completion_task_type: RephraseTaskType
    text: str
    app_name: Optional[str] = None
    uid: Optional[str] = None
    prev_rewrites: Optional[list] = None
    ls_order_product_id: Optional[str] = None

