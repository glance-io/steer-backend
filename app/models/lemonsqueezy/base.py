from typing import Any, Dict, Optional

from pydantic import BaseModel


class RelationshipLink(BaseModel):
    related: str
    self: str


class RelationshipEntity(BaseModel):
    links: RelationshipLink


class BaseLemonsqueezyDataModel(BaseModel):
    type: str
    id: int
    relationships: Optional[Any] = None
    links: Optional[Dict[str, Any]] = None
    attributes: Any
