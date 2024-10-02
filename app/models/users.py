import uuid
from typing import Optional

from pydantic import BaseModel


class SignInDTO(BaseModel):
    user_id: str | uuid.UUID
    license_id: Optional[str] = None
    order_product_id: Optional[str] = None
