from pydantic import BaseModel, HttpUrl
from typing import Optional, Literal, List
from datetime import datetime

from app.models.lemonsqueezy.base import BaseLemonsqueezyDataModel


class FirstSubscriptionItem(BaseModel):
    id: Optional[int] = None
    subscription_id: Optional[int] = None
    price_id: Optional[int] = None
    quantity: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Urls(BaseModel):
    update_payment_method: Optional[HttpUrl] = None
    customer_portal: Optional[HttpUrl] = None


class SubscriptionAttributes(BaseModel):
    store_id: Optional[int] = None
    customer_id: Optional[int] = None
    order_id: Optional[int] = None
    order_item_id: Optional[int] = None
    product_id: Optional[int] = None
    variant_id: Optional[int] = None
    product_name: Optional[str] = None
    variant_name: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    status: str
    status_formatted: Optional[str] = None
    pause: Optional[str] = None
    cancelled: Optional[bool] = None
    trial_ends_at: Optional[datetime] = None
    billing_anchor: Optional[int] = None
    first_subscription_item: Optional[FirstSubscriptionItem] = None
    urls: Optional[Urls] = None
    renews_at: datetime
    ends_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    test_mode: Optional[bool] = None


class Subscription(BaseLemonsqueezyDataModel):
    type: Literal["subscriptions"]
    attributes: SubscriptionAttributes


class SubscriptionResponse(BaseModel):
    data: Subscription


class SubscriptionMultiResponse(BaseModel):
    data: List[Subscription]
