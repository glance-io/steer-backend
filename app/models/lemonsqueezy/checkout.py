import uuid
from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.lemonsqueezy.base import BaseLemonsqueezyDataModel


class ProductOptions(BaseModel):
    name: str = ""
    description: str = ""
    media: List[str] = []
    redirect_url: str = ""
    receipt_button_text: str = ""
    receipt_link_url: str = ""
    receipt_thank_you_note: str = ""
    enabled_variants: List[int] = []


class CheckoutOptions(BaseModel):
    embed: bool = False
    media: bool = True
    logo: bool = True
    desc: bool = True
    discount: bool = True
    dark: bool = False
    subscription_preview: bool = True
    button_color: str = "#7047EB"


class CheckoutData(BaseModel):
    email: str = ""
    name: str = ""
    tax_number: str = ""
    discount_code: str = ""
    custom: dict = {}
    variant_quantities: List[dict] = []


class CheckoutAttributes(BaseModel):
    store_id: int
    variant_id: int
    custom_price: Optional[int] = None
    product_options: ProductOptions = ProductOptions()
    checkout_options: CheckoutOptions = CheckoutOptions()
    checkout_data: CheckoutData = CheckoutData()
    preview: bool
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    test_mode: bool = False
    url: str


class Checkout(BaseLemonsqueezyDataModel):
    id: uuid.UUID
    attributes: CheckoutAttributes
    type: Literal["checkouts"]


class CheckoutResponse(BaseModel):
    data: Checkout
