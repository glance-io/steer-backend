from enum import Enum

from app.models.lemonsqueezy.base import BaseLemonsqueezyDataModel
from typing import Optional, List, Union, Literal
from pydantic import BaseModel
from datetime import datetime


class Tier(BaseModel):
    last_unit: Union[int, str]
    unit_price: Optional[int] = None
    unit_price_decimal: Optional[str] = None
    fixed_fee: Optional[int] = None


class PriceCategory(str, Enum):
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    LEAD_MAGNET = "lead_magnet"
    PWYW = "pwyw"


class PriceRenewalUnit(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class PriceAttributes(BaseModel):
    variant_id: int
    category: PriceCategory
    scheme: str
    usage_aggregation: Optional[str] = None
    unit_price: Optional[int] = None
    unit_price_decimal: Optional[str] = None
    setup_fee_enabled: Optional[bool] = None
    setup_fee: Optional[int] = None
    package_size: int
    tiers: Optional[List[Tier]] = None
    renewal_interval_unit: Optional[str] = PriceRenewalUnit
    renewal_interval_quantity: Optional[int] = None
    trial_interval_unit: Optional[str] = None
    trial_interval_quantity: Optional[int] = None
    min_price: Optional[int] = None
    suggested_price: Optional[int] = None
    tax_code: str
    created_at: datetime
    updated_at: datetime

    @property
    def is_subscription(self):
        return self.category == PriceCategory.SUBSCRIPTION

    @property
    def is_lifetime(self):
        # TODO: figure out more checks
        return not self.is_subscription


class Price(BaseLemonsqueezyDataModel):
    type: Literal["prices"]
    attributes: PriceAttributes


class PriceResponse(BaseModel):
    data: Price