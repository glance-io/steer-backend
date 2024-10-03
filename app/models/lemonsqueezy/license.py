from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class LicenseKey(BaseModel):
    # Lemonsqueezy doesn't explicitly say which fields are nullable, so all fields not necessary are nullable
    id: Optional[int] = None
    status: str     # should be enum, but they don't provide the possible values
    key: Optional[UUID] = None
    activation_limit: Optional[int] = None
    activation_usage: Optional[int] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class Instance(BaseModel):
    id: Optional[UUID] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None


class Meta(BaseModel):
    # Lemonsqueezy doesn't explicitly say which fields are nullable, so all fields not necessary are nullable
    store_id: Optional[int] = None
    order_id: Optional[int] = None
    order_item_id: int
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    variant_id: Optional[int] = None
    variant_name: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None


class LicenseResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
    license_key: LicenseKey
    instance: Instance
    meta: Meta
