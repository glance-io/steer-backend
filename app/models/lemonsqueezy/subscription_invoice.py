from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field

from app.models.lemonsqueezy.base import BaseLemonsqueezyDataModel

from enum import Enum


class InvoiceStatus(str, Enum):
    pending = 'pending'
    paid = 'paid'
    void = 'void'
    refunded = 'refunded'
    partial_refund = 'partial_refund'

    def __str__(self):
        return self.value

class Urls(BaseModel):
    invoice_url: str


class SubscriptionInvoiceAttributes(BaseModel):
    store_id: int
    subscription_id: int
    customer_id: int
    user_name: str
    user_email: str
    billing_reason: str
    card_brand: str
    card_last_four: str
    currency: str
    currency_rate: float
    status: InvoiceStatus
    status_formatted: str
    refunded: bool
    refunded_at: Optional[str] = None
    subtotal: int
    discount_total: int
    tax: int
    tax_inclusive: bool
    total: int
    refunded_amount: int
    subtotal_usd: int
    discount_total_usd: int
    tax_usd: int
    total_usd: int
    refunded_amount_usd: int
    subtotal_formatted: str
    discount_total_formatted: str
    tax_formatted: str
    total_formatted: str
    refunded_amount_formatted: str
    urls: Urls
    created_at: str
    updated_at: str
    test_mode: bool


class SubscriptionInvoice(BaseLemonsqueezyDataModel):
    attributes: SubscriptionInvoiceAttributes
    type: Literal["subscription-invoices"]
