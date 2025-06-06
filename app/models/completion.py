from enum import Enum
from typing import Optional

from pydantic import BaseModel as PydanticBaseModel


class RephraseTaskType(str, Enum):
    FIX_GRAMMAR = "fix_grammar"
    REPHRASE = "rephrase"
    ADVANCED_IMPROVE = "advanced_improve"
    CONCISE = "concise"


class RephraseRequest(PydanticBaseModel):
    completion_task_type: RephraseTaskType
    text: str
    app_name: Optional[str] = None
    uid: str
    prev_rewrites: Optional[list] = None
    locale: Optional[str] = None  # e.g., en_US, en_GB, en_AU
