from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Literal

from app.models.lemonsqueezy.base import BaseLemonsqueezyDataModel, RelationshipEntity


class StatusEnum(str, Enum):
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    ARCHIVED = "archived"
    REQUIRES_VERIFICATION = "requires_verification"
    INVALID_EMAIL = "invalid_email"
    BOUNCED = "bounced"


class Urls(BaseModel):
    customer_portal: str


class CustomerAttributes(BaseModel):
    store_id: int
    name: str
    email: str
    status: StatusEnum
    city: Optional[str] = None
    region: Optional[str] = None
    country: str
    total_revenue_currency: float
    mrr: float
    status_formatted: str
    country_formatted: str
    total_revenue_currency_formatted: str
    mrr_formatted: str
    urls: Urls
    created_at: str
    updated_at: str
    test_mode: bool


class CustomerRelationships(BaseModel):
    orders: RelationshipEntity
    subscriptions: RelationshipEntity


class Customer(BaseLemonsqueezyDataModel):
    attributes: CustomerAttributes
    type: Literal["customers"]
    relationships: CustomerRelationships = Field(..., alias="relationships")


class CustomerResponse(BaseModel):
    data: Customer

