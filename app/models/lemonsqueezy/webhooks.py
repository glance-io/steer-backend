from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.models.lemonsqueezy.license_key import LicenseKey
from app.models.lemonsqueezy.order import Order
from app.models.lemonsqueezy.subscription import Subscription
from app.models.lemonsqueezy.subscription_invoice import SubscriptionInvoice


class EventType(str, Enum):
    ORDER_CREATED = "order_created"
    ORDER_REFUNDED = "order_refunded"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    SUBSCRIPTION_RESUMED = "subscription_resumed"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    SUBSCRIPTION_PAUSED = "subscription_paused"
    SUBSCRIPTION_UNPAUSED = "subscription_unpaused"
    SUBSCRIPTION_PAYMENT_SUCCESS = "subscription_payment_success"
    SUBSCRIPTION_PAYMENT_FAILED = "subscription_payment_failed"
    SUBSCRIPTION_PAYMENT_RECOVERED = "subscription_payment_recovered"
    SUBSCRIPTION_PAYMENT_REFUNDED = "subscription_payment_refunded"
    LICENSE_KEY_CREATED = "license_key_created"
    LICENSE_KEY_UPDATED = "license_key_updated"


class WebhookMeta(BaseModel):
    event_name: EventType
    custom_data: Optional[Dict[str, Any]] = None


class WebhookPayload(BaseModel):
    meta: WebhookMeta
    data: Subscription | LicenseKey | SubscriptionInvoice | Order = Field(..., discriminator="type")
