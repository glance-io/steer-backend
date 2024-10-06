from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel

from app.models.lemonsqueezy.base import BaseLemonsqueezyDataModel


class LicenseKeyAttributes(BaseModel):
    store_id: int
    customer_id: int
    order_id: int
    order_item_id: int
    product_id: int
    user_name: str
    user_email: str
    key: str
    key_short: str
    activation_limit: int
    instances_count: int = 0
    disabled: bool = False
    status: str
    status_formatted: str
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class LicenseKey(BaseLemonsqueezyDataModel):
    type: Literal["license-keys"]
    attributes: LicenseKeyAttributes
