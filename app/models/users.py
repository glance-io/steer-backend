import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SignInDTO(BaseModel):
    user_id: str | uuid.UUID
    instance_id: str
    license_key: str


class User(BaseModel):
    id: uuid.UUID
    email: str
    license_key: Optional[str] = None
    instance_id: Optional[str] = None
    subscription_id: Optional[str] = None
    is_premium: bool = False


class Usage(BaseModel):
    time_from: datetime
    time_to: datetime
    usage: int


class UserWithUsage(User):
    usage: Optional[Usage] = None
