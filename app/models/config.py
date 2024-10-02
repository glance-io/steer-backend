from pydantic import BaseModel


class DBConfig(BaseModel):
    url: str
    password: str