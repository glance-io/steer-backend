import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.config import ThrottlingConfig


class SignInDTO(BaseModel):
    instance_id: Optional[str] = None
    license_key: Optional[str] = None


class User(BaseModel):
    id: uuid.UUID
    email: str
    license_key: Optional[str] = None
    instance_id: Optional[str] = None
    subscription_id: Optional[int] = None
    variant_id: Optional[int] = None
    is_premium: bool = False
    lemonsqueezy_id: Optional[int] = None
    tier: str
    premium_until: Optional[datetime] = None


class Usage(BaseModel):
    time_from: datetime
    time_to: datetime
    usage: int


class UserWithUsage(User):
    period_usage: Optional[Usage] = None
    throttling_meta: ThrottlingConfig
