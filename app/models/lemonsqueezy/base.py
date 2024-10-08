from typing import Any, Dict, Optional

from pydantic import BaseModel


class BaseLemonsqueezyDataModel(BaseModel):
    type: str
    id: str
    relationships: Optional[Any] = None
    links: Optional[Dict[str, Any]] = None
    attributes: Any
