from datetime import datetime
from typing import Literal, Optional, List

from pydantic import BaseModel, Field

from app.models.lemonsqueezy.base import BaseLemonsqueezyDataModel, RelationshipEntity


class Link(BaseModel):
    title: str
    url: str


class VariantAttributes(BaseModel):
    product_id: int
    name: str
    slug: str
    description: str
    has_license_keys: bool
    license_activation_limit: int
    is_license_limit_unlimited: bool
    license_length_value: int
    license_length_unit: str
    is_license_length_unlimited: bool
    sort: int
    status: str
    status_formatted: str
    created_at: datetime
    updated_at: datetime
    test_mode: bool
    links: Optional[List[Link]] = None


class VariantRelationships(BaseModel):
    product: Optional[RelationshipEntity] = None
    files: Optional[RelationshipEntity] = None
    price_model: RelationshipEntity = Field(..., alias="price-model")


class Variant(BaseLemonsqueezyDataModel):
    type: Literal["variants"]
    attributes: VariantAttributes
    relationships: VariantRelationships = Field(..., alias="relationships")


class VariantResponse(BaseModel):
    data: Variant