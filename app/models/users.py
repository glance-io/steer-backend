import uuid
from typing import Optional

from pydantic import BaseModel


class SignInDTO(BaseModel):
    user_id: str | uuid.UUID
    instance_id: str
    license_key: str
