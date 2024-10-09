import json

from pydantic import BaseModel

from app.models.lemonsqueezy.base import BaseLemonsqueezyDataModel
from typing import Optional, List, Literal
from enum import Enum
from pydantic import BaseModel, Field


class Status(str, Enum):
    PENDING = "pending"
    FAILED = "failed"
    PAID = "paid"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"
    FRAUDULENT = "fraudulent"


class OrderItem(BaseModel):
    id: int
    order_id: int
    product_id: int
    variant_id: int
    product_name: str
    variant_name: str
    price: float
    created_at: str
    updated_at: str
    test_mode: bool


class Urls(BaseModel):
    receipt: str


class OrderAttributes(BaseModel):
    store_id: int
    customer_id: int
    identifier: str
    order_number: int
    user_name: str
    user_email: str
    currency: str
    currency_rate: float
    subtotal: float
    setup_fee: float
    discount_total: float
    tax: float
    total: float
    refunded_amount: Optional[float] = None
    subtotal_usd: float
    setup_fee_usd: float
    discount_total_usd: float
    tax_usd: float
    total_usd: float
    refunded_amount_usd: Optional[float] = None
    tax_name: str
    tax_rate: float
    tax_inclusive: bool
    status: Status
    status_formatted: str
    refunded: bool
    refunded_at: Optional[str] = None
    subtotal_formatted: str
    setup_fee_formatted: str
    discount_total_formatted: str
    tax_formatted: str
    total_formatted: str
    refunded_amount_formatted: Optional[str] = None
    first_order_item: OrderItem
    urls: Optional[Urls] = None
    created_at: str
    updated_at: str
    test_mode: bool

    class Config:
        use_enum_values = True


class Order(BaseLemonsqueezyDataModel):
    type: Literal["orders"]
    attributes: OrderAttributes


class OrderMultiResponse(BaseModel):
    data: List[Order]

